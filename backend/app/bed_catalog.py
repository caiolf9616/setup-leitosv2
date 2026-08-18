"""Catálogo oficial de enfermarias e leitos.

``key`` é o identificador técnico, único no banco. ``label`` é o nome real
mostrado nas telas. Essa separação permite que várias unidades tenham uma
enfermaria "01" sem qualquer ambiguidade.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WardCatalog:
    key: str
    label: str
    beds: tuple[str, ...]


def _numbers(start: int, end: int, width: int = 0) -> tuple[str, ...]:
    return tuple(f"{number:0{width}d}" for number in range(start, end + 1))


def _ward(unit: str, label: str, beds: tuple[str, ...]) -> WardCatalog:
    return WardCatalog(key=f"{unit}-{label}", label=label, beds=beds)


UNIT_CATALOG: dict[str, tuple[str, tuple[WardCatalog, ...]]] = {
    # unit_group: (nome de exibição, wards)
    "UCC": ("UCC", (_ward("UCC", "01", _numbers(1, 19)),)),
    "RISCO": ("Risco", (_ward("RISCO", "01", _numbers(1, 15)),)),
    "UTI-SEMI INTENSIVA": (
        "UTI-Semi Intensiva",
        (
            _ward("UTI-SEMI INTENSIVA", "101", _numbers(1, 2, 2)),
            _ward("UTI-SEMI INTENSIVA", "102", _numbers(3, 4, 2)),
            _ward("UTI-SEMI INTENSIVA", "103", _numbers(5, 6, 2)),
            _ward("UTI-SEMI INTENSIVA", "104", _numbers(7, 8, 2)),
            _ward("UTI-SEMI INTENSIVA", "105", _numbers(9, 10, 2)),
            _ward("UTI-SEMI INTENSIVA", "106", _numbers(11, 12, 2)),
            _ward("UTI-SEMI INTENSIVA", "ISO", _numbers(1, 2, 2)),
        ),
    ),
    "A": (
        "Unidade A",
        (
            _ward("A", "403", _numbers(11, 14)),
            _ward("A", "404", _numbers(15, 18)),
            _ward("A", "405", _numbers(19, 20)),
            _ward("A", "406", _numbers(23, 24)),
            _ward("A", "408", _numbers(27, 30)),
            _ward("A", "409", _numbers(31, 33)),
            _ward("A", "410", _numbers(34, 37)),
            _ward("A", "411", _numbers(38, 40)),
            _ward("A", "412", _numbers(41, 46)),
        ),
    ),
    "B": (
        "Unidade B",
        tuple(
            _ward(
                "B",
                str(room),
                {
                    201: ("01", "02", "03"),
                    202: ("04", "05"),
                    203: ("06", "07"),
                    204: ("08", "09"),
                    205: ("10", "11"),
                    206: ("12", "13"),
                    207: ("14", "15"),
                    208: ("16", "17"),
                    209: ("18", "19"),
                    210: ("20", "21"),
                    211: ("22", "23"),
                    212: ("24", "25", "26"),
                }[room],
            )
            for room in range(201, 213)
        ),
    ),
    "C": (
        "Unidade C",
        tuple(
            _ward(
                "C",
                str(room),
                (
                    _numbers(1, 3, 2)
                    if room == 300
                    else _numbers(24, 26, 2)
                    if room == 311
                    else _numbers(4 + (room - 301) * 2, 5 + (room - 301) * 2, 2)
                ),
            )
            for room in range(300, 312)
        ),
    ),
    "D": (
        "Unidade D",
        tuple(
            _ward("D", f"{room:02d}", _numbers(1 + (room - 1) * 12, room * 12, 2))
            for room in range(1, 5)
        ),
    ),
    "G": (
        "Unidade G",
        (
            *(
                _ward("G", str(room), _numbers(2 + (room - 602) * 4, 5 + (room - 602) * 4, 2))
                for room in range(602, 607)
            ),
            *(
                _ward("G", str(room), _numbers(22 + (room - 607) * 2, 23 + (room - 607) * 2, 2))
                for room in range(607, 614)
            ),
            _ward("G", "614", _numbers(36, 42, 2)),
        ),
    ),
    "H": (
        "Unidade H",
        (
            _ward("H", "701", _numbers(1, 2)),
            *(
                _ward("H", str(room), _numbers(3 + (room - 702) * 4, 6 + (room - 702) * 4))
                for room in range(702, 707)
            ),
            *(
                _ward("H", str(room), _numbers(23 + (room - 707) * 2, 24 + (room - 707) * 2))
                for room in range(707, 711)
            ),
        ),
    ),
    "I": (
        "Unidade I",
        (
            _ward("I", "801", _numbers(1, 4, 2)),
            _ward("I", "802", _numbers(5, 8, 2)),
            _ward("I", "803", _numbers(9, 10, 2)),
            _ward("I", "804", _numbers(11, 12, 2)),
            _ward("I", "805", _numbers(13, 16, 2)),
            _ward("I", "806", _numbers(17, 20, 2)),
            _ward("I", "807", _numbers(21, 22, 2)),
            _ward("I", "808", _numbers(23, 24, 2)),
            _ward("I", "809", _numbers(25, 28, 2)),
        ),
    ),
    "J": (
        "Unidade J",
        (
            _ward("J", "901", _numbers(1, 4, 2)),
            _ward("J", "902", _numbers(5, 8, 2)),
            _ward("J", "903", _numbers(9, 10, 2)),
            _ward("J", "904", _numbers(11, 12, 2)),
            _ward("J", "905", _numbers(13, 16, 2)),
            _ward("J", "906", _numbers(17, 20, 2)),
            _ward("J", "907", _numbers(21, 22, 2)),
            _ward("J", "908", _numbers(23, 24, 2)),
            _ward("J", "909", _numbers(25, 28, 2)),
        ),
    ),
}


def validate_catalog() -> None:
    keys: set[str] = set()
    for unit_group, (_, wards) in UNIT_CATALOG.items():
        for ward in wards:
            if ward.key in keys:
                raise ValueError(f"Enfermaria técnica duplicada: {ward.key}")
            keys.add(ward.key)
            if len(ward.beds) != len(set(ward.beds)):
                raise ValueError(f"Leito duplicado em {unit_group}/{ward.label}")


validate_catalog()
