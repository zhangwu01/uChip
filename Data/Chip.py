import typing
from typing import Optional, List, Dict, Any, Union, Callable, Type
from pathlib import Path
import os


class Chip:
    def __init__(self):
        self.valves: List[Valve] = []
        self.images: List[Image] = []
        self.text: List[Text] = []
        self.programs: List[Program] = []
        self.scripts: List[Script] = []

        builtinFiles = Path("Builtins").iterdir()
        for x in builtinFiles:
            f = open(x)
            self.scripts.append(Script(None, True, f.read(), x.stem))
            f.close()

    def ConvertPathsToRelative(self, basePath: Path):
        for image in self.images:
            image.path = Path(os.path.relpath(image.path, basePath))
        for script in self.scripts:
            if script.isBuiltIn:
                continue
            script.path = Path(os.path.relpath(script.path, basePath))

    def ConvertPathsToAbsolute(self, basePath: Path):
        for image in self.images:
            image.path = (basePath / image.path).absolute()
        for script in self.scripts:
            if script.isBuiltIn:
                continue
            script.path = (basePath / script.path).absolute()

class Valve:
    def __init__(self):
        self.name = ""
        self.rect = [0, 0, 0, 0]
        self.solenoidNumber = 0


class Text:
    def __init__(self):
        self.rect = [0, 0, 0, 0]
        self.fontSize = 12
        self.text = "New annotation"
        self.color = (0, 0, 0)


class Image:
    def __init__(self):
        self.rect = [0, 0, 0, 0]
        self.path: Optional[Path] = None


class Script:
    def __init__(self, path: Optional[Path], isBuiltIn=False, biScript="", biName=""):
        self.path: Path = path
        self.isBuiltIn = isBuiltIn
        self.biScript = biScript
        self.biName = biName

    def Read(self):
        if self.isBuiltIn:
            return self.biScript
        scriptFile = open(self.path, "r")
        script = scriptFile.read()
        scriptFile.close()
        return script

    def Name(self):
        if self.isBuiltIn:
            return self.biName
        return self.path.stem


class Program:
    def __init__(self, script):
        self.script = script
        self.position = [0, 0]
        self.scale = 1
        self.parameterValues: Dict[str, Any] = {}
        self.parameterVisibility: Dict[str, Any] = {}
        self.name = ""
        self.hideMessages = False

    def __setstate__(self, state):
        if "hideMessages" not in state:
            state["hideMessages"] = False
        self.__dict__ = state
