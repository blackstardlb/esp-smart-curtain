import json
import ulogging

log = ulogging.getLogger("utils")
log.setLevel(ulogging.DEBUG)


def _write_json_file(file_name, data):
    f = open(file_name, 'w')
    f.write(json.dumps(data))
    f.close()
    log.debug("Wrote to file: %s data: %s", file_name, data)


def _read_json_file(file_name):
    f = open(file_name, 'r')
    data = json.loads(f.read())
    f.close()
    log.debug("Read from file: %s data: %s", file_name, data)
    return data


def write_secrets(data):
    _write_json_file("secrets.json", data)


def read_secrets():
    return _read_json_file("secrets.json")


class NamedEnum:  # pylint: disable=too-few-public-methods
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __eq__(self, other):
        if isinstance(other, NamedEnum):
            return self.value == other.value
        return False


def _flatten_dict_gen(d, parent_key, sep):
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            yield from flatten_dict(v, new_key, sep=sep).items()
        else:
            yield new_key, v


def flatten_dict(d: dict, parent_key: str = '', sep: str = '.'):
    return dict(_flatten_dict_gen(d, parent_key, sep))
