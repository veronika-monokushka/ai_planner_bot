import os
import json
from pathlib import Path

def prepare_for_ai(root_dir="src", max_file_size=10000):
    """Подготавливает проект для отправки AI"""
    result = {
        "structure": {},
        "files": {}
    }
    
    for py_file in Path(root_dir).rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        
        rel_path = str(py_file)
        size = py_file.stat().st_size
        
        result["structure"][rel_path] = {
            "size": size,
            "lines": len(py_file.read_text(encoding='utf-8').splitlines())
        }
        
        # Если файл не слишком большой, включаем содержимое
        if size < max_file_size:
            result["files"][rel_path] = py_file.read_text(encoding='utf-8')
    
    # Сохраняем
    with open("ai_context.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Обработано {len(result['structure'])} файлов")
    print(f"📦 Размер: {len(json.dumps(result)) // 1024} KB")

if __name__ == "__main__":
    prepare_for_ai()