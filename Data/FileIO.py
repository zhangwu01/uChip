#------------------- macOS Platform ------------------------
import dill
from pathlib import PosixPath


class CrossPlatformUnpickler(dill.Unpickler):
    def find_class(self, module, name):
        # Redirect WindowsPath to PosixPath on macOS/Linux
        if module == 'pathlib' and name == 'WindowsPath':
            return PosixPath
        return super().find_class(module, name)

def LoadObject(file_path):
    """Load a dill/pickle object from file, fixing WindowsPath on non-Windows systems."""
    with open(file_path, 'rb') as file:
        return CrossPlatformUnpickler(file).load()


def SaveObject(obj, file_path):
    """Save a dill/pickle object to file."""
    with open(file_path, 'wb') as file:
        dill.dump(obj, file)





#------------------- Windows Platform ------------------------
# import dill
# from pathlib import Path

# def LoadObject(path: Path):
#     file = open(path, "rb")
#     obj = dill.load(file)
#     file.close()
#     return obj


# def SaveObject(obj, path: Path):
#     file = open(path, "wb+")
#     dill.dump(obj, file)
#     file.close()
