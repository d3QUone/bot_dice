import json
import os
from dataclasses import is_dataclass, asdict
from typing import Any, List


class Storage:
    """ Хранилище для сбрасывания более-менее важной информации на диск.
        Данный бот не предполагает никакой нагрузки или сложной логики, поэтому просто сохраним
        промежуточные результаты для более мягкого деплоя.
    """
    def __init__(self, filename: str, klass, base_path: str = None, dry_run: bool = False):
        self.base_path = base_path or os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.filename = f'{filename}.json'
        self.path = os.path.join(self.base_path, self.filename)
        self.klass = klass
        self.dry_run = dry_run

    def save(self, objs: List[Any]):
        assert all([is_dataclass(i) for i in objs]), 'Only dataclasses allowed here!'
        if self.dry_run:
            return

        data = [asdict(i) for i in objs]
        with open(self.path, 'w+') as fp:
            json.dump(obj=data, fp=fp)

    def load(self) -> List[Any]:
        if self.dry_run:
            return []

        if not os.path.isfile(self.path):
            return []
        with open(self.path, 'r') as fp:
            data = json.load(fp=fp)
        res = [self.klass(**i) for i in data]
        return res
