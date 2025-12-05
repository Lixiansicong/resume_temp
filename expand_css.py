import os
import re
import glob
import sys

class Node:
    def __init__(self, selector, parent=None):
        self.selector = selector
        self.parent = parent
        self.children = []
        self.properties = []
        
    @property
    def is_at_rule(self):
        return self.selector.startswith('@')

def parse_css(css_text):
    # 移除注释
    css_text = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
    
    root = Node("root")
    current = root
    stack = [root]
    
    buffer = ""
    in_string = False
    string_char = None
    
    i = 0
    while i < len(css_text):
        char = css_text[i]
        
        if in_string:
            if char == string_char:
                # 简单的转义检查
                if i > 0 and css_text[i-1] == '\\' and (i < 2 or css_text[i-2] != '\\'):
                    pass 
                else:
                    in_string = False
            buffer += char
        else:
            if char == '"' or char == "'":
                in_string = True
                string_char = char
                buffer += char
            elif char == '{':
                selector = buffer.strip()
                new_node = Node(selector, parent=current)
                current.children.append(new_node)
                current = new_node
                stack.append(current)
                buffer = ""
            elif char == '}':
                prop = buffer.strip()
                if prop:
                    current.properties.append(prop)
                
                if len(stack) > 1:
                    stack.pop()
                    current = stack[-1]
                buffer = ""
            elif char == ';':
                buffer += char
                prop = buffer.strip()
                if prop:
                    current.properties.append(prop)
                buffer = ""
            else:
                buffer += char
        i += 1
    
    return root

def flatten_node(node, prefix="", results=None):
    if results is None:
        results = []
        
    current_selector = ""
    
    if node.selector == "root":
        pass
    elif node.is_at_rule:
        # @media 等规则，不直接拼接前缀，而是将前缀传递给内部
        pass 
    else:
        if prefix:
            if node.selector.startswith('&'):
                current_selector = prefix + node.selector[1:]
            else:
                current_selector = prefix + " " + node.selector
        else:
            current_selector = node.selector

    if node.selector != "root":
        if node.is_at_rule:
            results.append(f"{node.selector} {{")
            
            # At-rule 自身的属性（如 @font-face 内部属性）
            if node.properties:
                # 检查是否有前缀，如果有前缀且属性存在，可能是在嵌套结构中
                # 但标准 CSS Parser 逻辑里，@media 内部通常是规则
                # 如果是嵌套写法: .box { @media { color: red } } -> @media { .box { color: red } }
                if prefix:
                    results.append(f"  {prefix} {{")
                    for p in node.properties:
                        results.append(f"    {p}")
                    results.append("  }")
                else:
                    for p in node.properties:
                        results.append(f"  {p}")
            
            # 递归处理子节点
            for child in node.children:
                flatten_node(child, prefix, results) # 保持外部的前缀传入 @media 内部

            results.append("}")
            return
            
        else:
            if node.properties:
                results.append(f"{current_selector} {{")
                for p in node.properties:
                    results.append(f"  {p}")
                results.append("}")
    
    next_prefix = current_selector if (node.selector != "root" and not node.is_at_rule) else prefix
    
    for child in node.children:
        flatten_node(child, next_prefix, results)

def process_file(filepath):
    print(f"Processing {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找并替换 <style> 块
        pattern = re.compile(r'(<style[^>]*>)(.*?)(</style>)', re.DOTALL | re.IGNORECASE)
        
        def replace_style(match):
            open_tag = match.group(1)
            css_content = match.group(2)
            close_tag = match.group(3)
            
            if not css_content.strip():
                return match.group(0)
                
            try:
                root = parse_css(css_content)
                flattened_lines = []
                flatten_node(root, "", flattened_lines)
                new_css = "\n".join(flattened_lines)
                return f"{open_tag}\n{new_css}\n{close_tag}"
            except Exception as e:
                print(f"Error parsing CSS in {filepath}: {e}")
                return match.group(0)
        
        new_content = pattern.sub(replace_style, content)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
    except Exception as e:
        print(f"Failed to process {filepath}: {e}")

if __name__ == "__main__":
    # 默认行为：搜索 moban/d*.html 并处理
    # 也可以接受命令行参数传入特定文件
    
    targets = []
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        # 默认逻辑
        targets = sorted(glob.glob('demo*.html'))
    
    if not targets:
        print("没有找到目标文件。用法: python3 expand_css.py [文件路径...]")
    else:
        print(f"找到 {len(targets)} 个文件待处理")
        for t in targets:
            process_file(t)
