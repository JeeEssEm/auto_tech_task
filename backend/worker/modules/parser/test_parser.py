"""
Базовые тесты для парсера
"""
import sys
import os
from pathlib import Path

from backend.worker.modules.parser import parse


def test_imports():
    """Тест импорта всех модулей"""
    print("Testing imports...")
    try:
        from backend.worker.modules.parser import UniversalParser, parse
        print("✓ UniversalParser and parse imported successfully")
        
        from backend.worker.modules.parser.exceptions import (
            ExtractorNotFound,
            ParserConfigError,
            TranscriptionError
        )
        print("✓ All exceptions imported successfully")
        
        from backend.worker.modules.parser.extractors import (
            TextExtractor,
            JsonExtractor,
            OfficeExtractor,
            AudioExtractor,
            VideoExtractor,
        )
        print("✓ All extractors imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False


def test_parser_initialization():
    """Тест инициализации парсера"""
    print("\nTesting parser initialization...")
    try:
        from backend.worker.modules.parser import UniversalParser
        
        # Тестируем с дефолтом
        parser = UniversalParser()
        print("✓ Parser initialized with defaults (base model)")
        
        # Тестируем с tiny моделью
        parser = UniversalParser(whisper_model='tiny')
        print("✓ Parser initialized with 'tiny' whisper model")
        
        # Тестируем с small моделью
        parser = UniversalParser(whisper_model='small')
        print("✓ Parser initialized with 'small' whisper model")
        
        # Тестируем отключение whisper
        parser = UniversalParser(use_whisper=False)
        print("✓ Parser initialized with whisper disabled")
        
        # Тестируем неправильную модель
        try:
            parser = UniversalParser(whisper_model='invalid_model')
            print("✗ Should have raised error for invalid model")
            return False
        except ValueError as e:
            print(f"✓ Correctly rejected invalid model: {e}")
        
        return True
    except Exception as e:
        print(f"✗ Initialization error: {e}")
        return False


def test_file_extension_parsing():
    """Тест парсинга расширения файла"""
    print("\nTesting file extension parsing...")
    try:
        from backend.worker.modules.parser import UniversalParser
        
        parser = UniversalParser()
        
        # Тестируем различные расширения
        test_cases = [
            ('document.pdf', 'pdf'),
            ('file.DOCX', 'docx'),
            ('audio.mp3', 'mp3'),
            ('video.mkv', 'mkv'),
            ('data.json', 'json'),
            ('readme.md', 'md'),
            ('file.txt', 'txt'),
        ]
        
        for filename, expected_ext in test_cases:
            ext = parser._get_file_extension(filename)
            if ext == expected_ext:
                print(f"✓ {filename} -> {ext}")
            else:
                print(f"✗ {filename} -> {ext} (expected {expected_ext})")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Extension parsing error: {e}")
        return False


def test_extractor_availability():
    """Тест доступности экстракторов"""
    print("\nTesting extractor availability...")
    try:
        from backend.worker.modules.parser import UniversalParser
        
        parser = UniversalParser()
        
        # Проверяем основные форматы
        formats = ['txt', 'md', 'json', 'pdf', 'docx', 'mp3', 'mp4']
        
        for fmt in formats:
            try:
                extractor = parser._get_extractor(fmt)
                print(f"✓ Extractor for '.{fmt}' is available")
            except Exception as e:
                print(f"✗ Extractor for '.{fmt}' error: {e}")
                return False
        
        # Проверяем что неизвестный format вызовет ошибку
        try:
            extractor = parser._get_extractor('unknown_format')
            print("✗ Should have raised ExtractorNotFound")
            return False
        except Exception:
            print("✓ ExtractorNotFound raised correctly for unknown format")
        
        return True
    except Exception as e:
        print(f"✗ Extractor availability error: {e}")
        return False


def test_extractor_messages():
    result = parse(r"C:\Users\JeeEssEm\Desktop\ChatExport_2026-03-07\result.json")
    path = Path(r"C:\Users\JeeEssEm\Desktop\ChatExport_2026-03-07\result.txt")
    path.write_text(result["text"], encoding="utf-8")


def run_all_tests():
    """Запустить все тесты"""
    print("=" * 60)
    print("Running Parser Tests")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_parser_initialization,
        test_file_extension_parsing,
        test_extractor_availability,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Test Results: {passed}/{total} passed")
    print("=" * 60)
    
    return all(results)


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
