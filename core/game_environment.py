"""Read-only checks for game settings used by automation."""

import hashlib
import os
import struct
import time
from pathlib import Path


# Nightreign's global profile is BND4 entry 10. A controlled in-game change
# from brightness 5 to 6 changed only byte 0x12 among its six setting bytes.
# The BND4 layout and AES key are documented in the open-source Nightreign
# parser: https://github.com/Hapfel1/er-save-manager/blob/main/src/er_save_manager/games/NR/parser.py
_SAVE_KEY = bytes.fromhex("18f6326605bd178a5524523ac0a0c609")
_PROFILE_ENTRY_INDEX = 10
_PROFILE_MAGIC = 0x00060010
_BRIGHTNESS_OFFSET = 0x12


def _read_brightness_from_save(raw):
    """Decrypt and validate only the global profile entry; never write data."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    if len(raw) < 64 + (_PROFILE_ENTRY_INDEX + 1) * 32 or raw[:4] != b"BND4":
        raise ValueError("存档格式无效")
    entry_count = struct.unpack_from("<I", raw, 12)[0]
    if entry_count <= _PROFILE_ENTRY_INDEX:
        raise ValueError("存档缺少全局设置区")

    entry_pos = 64 + _PROFILE_ENTRY_INDEX * 32
    if raw[entry_pos:entry_pos + 8] != b"\x40\x00\x00\x00\xff\xff\xff\xff":
        raise ValueError("存档全局设置区格式无效")
    size, _, offset = struct.unpack_from("<3i", raw, entry_pos + 8)
    if size < 32 or offset < entry_pos + 32 or offset + size > len(raw) or (size - 16) % 16:
        raise ValueError("存档全局设置区不完整")

    iv = raw[offset:offset + 16]
    ciphertext = raw[offset + 16:offset + size]
    decryptor = Cipher(algorithms.AES(_SAVE_KEY), modes.CBC(iv)).decryptor()
    profile = decryptor.update(ciphertext) + decryptor.finalize()
    if len(profile) < 48 or struct.unpack_from("<I", profile, 0)[0] != _PROFILE_MAGIC:
        raise ValueError("存档全局设置区解密失败")
    if hashlib.md5(profile[4:-28]).digest() != profile[-28:-12]:
        raise ValueError("存档全局设置区校验失败，可能正在保存")

    brightness = profile[_BRIGHTNESS_OFFSET]
    if not 0 <= brightness <= 10:
        raise ValueError("存档亮度值超出游戏设置范围")
    return brightness


def inspect_game_brightness(save_path=None):
    """Return (saved brightness, reason), reading a fresh save on every call.

    An unknown value remains unknown if the save is absent, ambiguous, being
    written, or cannot be decrypted. A running game's unsaved state is not read.
    """
    if save_path is None:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None, "未找到 APPDATA 目录"
        candidates = list((Path(appdata) / "Nightreign").glob("*/NR0000.sl2"))
        if not candidates:
            return None, "未找到 Nightreign 存档"
        if len(candidates) != 1:
            return None, "找到多个 Nightreign 账户存档，无法确定当前账户"
        save_path = candidates[0]

    for attempt in range(2):
        try:
            return _read_brightness_from_save(Path(save_path).read_bytes()), None
        except (OSError, ValueError, ImportError) as exc:
            if attempt:
                return None, f"无法读取或校验 Nightreign 存档：{exc}"
            time.sleep(0.1)  # The game may be auto-saving during the first read.


def log_brightness_check(log):
    """Report the current save's value without claiming to read game memory."""
    brightness, reason = inspect_game_brightness()
    if brightness == 5:
        log("游戏存档中的亮度设置为 5。", "INFO")
    elif brightness is not None:
        log(f"游戏存档中的亮度设置为 {brightness}；建议在游戏显示设置中调整为 5，"
            "以保证仓库遗物状态识别准确率。", "WARNING")
    else:
        log(f"无法核实游戏亮度是否为 5（{reason}）；"
            "请在游戏显示设置中确认亮度为 5，以保证仓库遗物状态识别准确率。", "WARNING")
