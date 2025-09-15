"""Simplified tests for CRA CLI tool core functionality using actual data."""

import tempfile
import os
import time
from pathlib import Path

from cra.config import Settings
from cra.utils import build_report_name, gc_reports, update_latest_report
from cra.dtos import CodeChange, DiffRecommendations
from cra.lint_tool.py_linters import has_python, run_linter
from cra.lint_tool.js_linters import has_javascript
from cra.lint_tool.main import run_linters, save_report


# Configuration Tests
class TestConfig:
    """Test configuration functionality."""
    
    def test_settings_initialization(self):
        """Test that Settings can be initialized with defaults."""
        settings = Settings()
        assert hasattr(settings, 'codebase_path')
        assert hasattr(settings, 'cache_dir')
        assert hasattr(settings, 'reports_dir')
        assert hasattr(settings, 'llm_model')
        assert settings.chunk_size > 0
        assert settings.chunk_overlap >= 0
    
    def test_reports_dir_path_property(self):
        """Test reports_dir_path property returns Path object."""
        settings = Settings()
        assert isinstance(settings.reports_dir_path, Path)
    
    def test_latest_report_path_property(self):
        """Test latest_report_path property returns correct path."""
        settings = Settings()
        latest_path = settings.latest_report_path
        assert latest_path.endswith('.latest_report.md')


# Utility Functions Tests
class TestUtils:
    """Test utility functions with actual data."""
    
    def test_build_report_name(self):
        """Test report name generation with actual data."""
        name = build_report_name('/test/path/my_project')
        assert name.startswith('my_project_')
        assert name.endswith('.md')
        assert len(name.split('_')) >= 3  # project_YYYY-MM-DD_HHMM.md
    
    def test_build_report_name_with_spaces(self):
        """Test report name with path containing spaces."""
        name = build_report_name('/test/my project name')
        assert 'my project name' in name
        assert name.endswith('.md')
    
    def test_gc_reports(self):
        """Test garbage collection of old reports with actual files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a temporary Settings instance for this test
            class TestSettings(Settings):
                def __init__(self, reports_dir):
                    self.reports_dir = reports_dir
                    self.keep_reports = 3
                    # Create directories
                    Path(self.reports_dir).mkdir(exist_ok=True)
                
                @property
                def reports_dir_path(self):
                    return Path(self.reports_dir)
            
            test_settings = TestSettings(tmpdir)
            
            # Create test files with different timestamps
            for i in range(5):
                file_path = Path(tmpdir) / f'report_{i}.md'
                file_path.touch()
                # Set different modification times
                os.utime(file_path, (time.time() - i*1000, time.time() - i*1000))
            
            # Save original settings
            from cra.utils import settings as original_settings
            
            # Temporarily replace the settings in the cra.utils module
            import cra.utils
            cra.utils.settings = test_settings
            
            try:
                gc_reports()
                
                remaining = list(Path(tmpdir).glob('*.md'))
                assert len(remaining) == 3
            finally:
                # Restore original settings
                cra.utils.settings = original_settings
    
    def test_update_latest_report(self):
        """Test updating latest report symlink with actual files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a temporary Settings instance for this test
            class TestSettings(Settings):
                def __init__(self, reports_dir):
                    self.reports_dir = reports_dir
                    # Create directories
                    Path(self.reports_dir).mkdir(exist_ok=True)
                
                @property
                def reports_dir_path(self):
                    return Path(self.reports_dir)
            
            test_settings = TestSettings(tmpdir)
            
            # Create a test report file
            new_report = Path(tmpdir) / 'new_report.md'
            new_report.write_text('# Test Report\n\nThis is a test report.')
            
            # Save original settings
            from cra.utils import settings as original_settings
            
            # Temporarily replace the settings in the cra.utils module
            import cra.utils
            cra.utils.settings = test_settings
            
            try:
                update_latest_report(new_report)
                
                latest = Path(tmpdir) / 'latest.md'
                assert latest.exists()
            finally:
                # Restore original settings
                cra.utils.settings = original_settings


# DTOs Tests
class TestDTOs:
    """Test data transfer objects with actual data."""
    
    def test_code_change_creation(self):
        """Test CodeChange object creation."""
        change = CodeChange(
            file_path='test.py',
            line_number=10,
            original_code='print("hello")',
            recommended_code='print("hello world")',
            reason='Improve message clarity',
            issue_type='style'
        )
        assert change.file_path == 'test.py'
        assert change.line_number == 10
        assert change.issue_type == 'style'
    
    def test_diff_recommendations_creation(self):
        """Test DiffRecommendations object creation."""
        change = CodeChange(
            file_path='test.py',
            line_number=5,
            original_code='old code',
            recommended_code='new code',
            reason='test reason',
            issue_type='pylint'
        )
        recommendations = DiffRecommendations(
            summary='Test summary',
            changes=[change],
            priority_order=['pylint', 'security']
        )
        assert recommendations.summary == 'Test summary'
        assert len(recommendations.changes) == 1
        assert recommendations.priority_order[0] == 'pylint'


# Language Detection Tests
class TestLanguageDetection:
    """Test language detection functionality with actual files."""
    
    def test_has_python_with_python_file(self):
        """Test has_python function with actual Python file."""
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as tmp:
            try:
                tmp.write(b'print("hello world")')
                tmp.flush()
                result = has_python(Path(tmp.name))
                assert result is True
            finally:
                os.unlink(tmp.name)
    
    def test_has_python_with_non_python_file(self):
        """Test has_python function with non-Python file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            try:
                tmp.write(b'This is a text file')
                tmp.flush()
                result = has_python(Path(tmp.name))
                assert result is False
            finally:
                os.unlink(tmp.name)
    
    def test_has_python_with_directory(self):
        """Test has_python function with directory containing Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / 'test.py').write_text('print("hello")')
            result = has_python(Path(tmpdir))
            assert result is True
    
    def test_has_javascript_with_js_file(self):
        """Test has_javascript function with actual JavaScript file."""
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tmp:
            try:
                tmp.write(b'console.log("hello world");')
                tmp.flush()
                result = has_javascript(Path(tmp.name))
                assert result is True
            finally:
                os.unlink(tmp.name)
    
    def test_has_javascript_with_non_js_file(self):
        """Test has_javascript function with non-JavaScript file."""
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as tmp:
            try:
                tmp.write(b'print("hello world")')
                tmp.flush()
                result = has_javascript(Path(tmp.name))
                assert result is False
            finally:
                os.unlink(tmp.name)


# Linting Tests
class TestLinting:
    """Test linting functionality with actual code."""
    
    def test_run_linter_with_actual_command(self):
        """Test run_linter function with actual command."""
        # Using echo command which should always be available
        result = run_linter(['echo'], 'test')
        assert 'test' in result
    
    def test_run_linters_with_python_file(self):
        """Test run_linters with actual Python file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test Python file
            test_file = Path(tmpdir) / 'test.py'
            test_file.write_text('print("hello world")')
            
            # Test that has_python detects the file
            assert has_python(Path(tmpdir)) is True
            
            # Run linters on the directory
            result = run_linters(str(tmpdir))
            assert '# Linting Report' in result
            assert str(tmpdir) in result
    
    def test_run_linters_with_javascript_file(self):
        """Test run_linters with actual JavaScript file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test JavaScript file
            test_file = Path(tmpdir) / 'test.js'
            test_file.write_text('console.log("hello world");')
            
            # Test that has_javascript detects the file
            assert has_javascript(Path(tmpdir)) is True
            
            # Run linters on the directory
            result = run_linters(str(tmpdir))
            assert '# Linting Report' in result
            assert str(tmpdir) in result
    
    def test_save_report(self):
        """Test save_report function with actual data."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            try:
                save_report('# Test Report\n\nThis is a test report.', tmp.name)
                
                with open(tmp.name, 'r') as f:
                    content = f.read()
                assert '# Test Report' in content
                assert 'This is a test report.' in content
            finally:
                os.unlink(tmp.name)


# Integration Tests
class TestIntegration:
    """Test integration between components with actual data."""
    
    def test_full_python_linting_workflow(self):
        """Test full Python linting workflow with actual files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test Python file with some issues
            test_file = Path(tmpdir) / 'test.py'
            test_file.write_text('''
import os
def test_function():
    x=5+3
    print(x)
    return x
''')
            
            # Test the full workflow
            result = run_linters(str(tmpdir))
            
            # Verify the report structure
            assert '# Linting Report' in result
            assert str(tmpdir) in result
            assert '## Python Linting Results' in result
            
            # Check that we have some content
            assert len(result) > 100  # Should have substantial content
    
    def test_full_javascript_linting_workflow(self):
        """Test full JavaScript linting workflow with actual files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test JavaScript file
            test_file = Path(tmpdir) / 'test.js'
            test_file.write_text('''
function testFunction() {
    var x = 5 + 3;
    console.log(x);
    return x;
}
''')
            
            # Test the full workflow
            result = run_linters(str(tmpdir))
            
            # Verify the report structure
            assert '# Linting Report' in result
            assert str(tmpdir) in result
            assert '## JavaScript Linting Results' in result
            
            # Check that we have some content
            assert len(result) > 100 # Should have substantial content