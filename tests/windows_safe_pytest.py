"""Run the complete suite using writable project-local temp paths on managed Windows."""
from hashlib import sha256
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
SAFE = ROOT / ".test-runtime"
SAFE.mkdir(parents=True, exist_ok=True)
RUN_ROOT = SAFE / "pytest-data" / uuid4().hex
RUN_ROOT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

# Streamlit's AppTest.from_string uses a module-level tempfile directory. In
# this managed Windows workspace, tempfile-created child ACLs deny writes.
import streamlit.testing.v1.app_test as app_test
app_test.TMP_DIR._finalizer.detach()
app_test.TMP_DIR.name = str(SAFE / "streamlit-app-test")
(SAFE / "streamlit-app-test").mkdir(parents=True, exist_ok=True)

import pytest

class SafeWorkspaceTemp:
    @pytest.fixture
    def tmp_path(self, request):
        key = sha256(request.node.nodeid.encode("utf-8")).hexdigest()[:20]
        path = RUN_ROOT / key
        path.mkdir(parents=True, exist_ok=True)
        return path


targets = sys.argv[1:] or [str(ROOT / "tests")]
raise SystemExit(pytest.main([*targets, "-q", "-p", "no:cacheprovider"], plugins=[SafeWorkspaceTemp()]))
