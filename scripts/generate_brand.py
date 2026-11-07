"""Rasterize the code-native Faultline application mark."""
import struct
import zlib
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'apps/mobile/assets'


def png(path, size, foreground=False, background=False, mono=False):
    pixels = bytearray()
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            nx, ny = x / size, y / size
            upper = 0.15 < ny < 0.54 and abs(nx - (0.64 - 0.43 * ny)) < 0.043
            lower = 0.46 < ny < 0.85 and abs(nx - (0.60 - 0.43 * ny)) < 0.043
            if (upper or lower) and not background:
                color = (246, 245, 235, 255)
            else:
                color = (0, 0, 0, 0) if foreground or mono else (32, 46, 39, 255)
            pixels.extend(color)

    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))

    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', size, size, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b''))


png(root / 'icon.png', 1024)
png(root / 'favicon.png', 64)
png(root / 'android-icon-foreground.png', 1024, foreground=True)
png(root / 'android-icon-background.png', 1024, background=True)
png(root / 'android-icon-monochrome.png', 1024, mono=True)
print('Generated Faultline application icons.')
