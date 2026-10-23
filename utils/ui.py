def key(module, name):
    """위젯 키 규칙: module_widget_name (DuplicateElementId 방지)"""
    return f"{module}_{name}"
