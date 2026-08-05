import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ConformanceMetadataTests(unittest.TestCase):
    def test_metadata_is_explicit_and_safe(self):
        data = json.loads((ROOT / "conformance" / "ide-integration.json").read_text())
        self.assertEqual("zed-pkg/ide-integration-conformance/v1", data["schema"])
        self.assertEqual("sublimetext", data["integration"])
        capabilities = data["capabilities"]
        for name in ("multiRootDiscovery", "manifestDiagnostics", "lockDiagnostics", "materializationDiagnostics", "stagingRecovery", "cliValidation", "argvExecution", "boundedExecution", "outputRedaction", "explicitMutationConfirmation", "deterministicFallback", "nativeUnitTests", "retainedArtifact"):
            self.assertIs(capabilities[name], True, name)

if __name__ == "__main__":
    unittest.main()
