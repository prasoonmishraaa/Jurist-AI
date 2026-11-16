import sys
import inspect
from pathlib import Path

sys.path.insert(0, str(Path("ml-service").resolve()))
from app.prediction.verified_outcome_model import TargetLeakageSanitizer

print(inspect.getsource(TargetLeakageSanitizer))
