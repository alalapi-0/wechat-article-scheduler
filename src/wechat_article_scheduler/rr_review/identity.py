"""Fixed native sealed-FD supply. Values remain inside the project process RAM."""
import array
import fcntl
import hmac
import os
from pathlib import Path
import socket
import stat
import struct

from .protocol import PROJECT, Refused, canonical, loads, need

KEY_SOCKET = '/run/rr-project-keys/key.sock'
BROWSER_SOCKET = '/run/rr-projects/' + PROJECT + '/browser.sock'
AGENT_SOCKET = '/run/rr-projects/' + PROJECT + '/agent.sock'
KEY_NAME = 'rrp-' + PROJECT + '-auth-key'
OWNER_UID, GATEWAY_UID, GATEWAY_GID = 1000, 996, 984


class SupplyNotReady(Refused):
    """Only pre-connection absence/refusal; never an invalid response or FD."""
    def __init__(self):
        super().__init__(503, 'key_supply_not_ready')


def peer(sock):
    return struct.unpack('3i', sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))


def physical(path):
    path = Path(path)
    need(path.is_absolute(), 503, 'native_path_invalid')
    for part in (path, *path.parents):
        need(not part.is_symlink(), 503, 'native_path_invalid')
    return path


def receive_key(path=KEY_SOCKET, *, provider_uid=GATEWAY_UID, provider_gid=GATEWAY_GID):
    """The override is only used by explicit public-fixture tests; no environment switch."""
    path = physical(path)
    try:
        directory, item = path.parent.stat(), path.lstat()
    except FileNotFoundError:
        raise SupplyNotReady() from None
    need(directory.st_uid == provider_uid and directory.st_gid == provider_gid and
         stat.S_IMODE(directory.st_mode) == 0o750 and stat.S_ISSOCK(item.st_mode) and
         item.st_uid == provider_uid and item.st_gid == provider_gid and
         stat.S_IMODE(item.st_mode) == 0o660, 503, 'key_supply_unavailable')
    received = []
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as client:
            client.settimeout(3)
            try:
                client.connect(str(path))
            except (FileNotFoundError, ConnectionRefusedError):
                raise SupplyNotReady() from None
            _, uid, gid = peer(client)
            need(uid == provider_uid and gid == provider_gid, 503, 'key_peer_invalid')
            client.sendall(canonical({'schema': 1, 'project_id': PROJECT, 'recipient_uid': OWNER_UID}) + b'\n')
            data, ancillary, flags, _ = client.recvmsg(513, socket.CMSG_SPACE(16), socket.MSG_CMSG_CLOEXEC)
            for level, kind, value in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    entries = array.array('i')
                    entries.frombytes(value[:len(value) - len(value) % entries.itemsize])
                    received.extend(entries)
            need(not flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC) and len(received) == 1 and
                 len(ancillary) == 1 and data == canonical({'schema': 1, 'project_id': PROJECT, 'key_fd': True}) + b'\n',
                 503, 'key_packet_invalid')
            fd = received[0]
            info = os.fstat(fd)
            need(stat.S_ISREG(info.st_mode) and info.st_nlink == 0 and info.st_uid == provider_uid and
                 info.st_gid == provider_gid and stat.S_IMODE(info.st_mode) == 0o400 and 32 <= info.st_size <= 64 and
                 fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY and
                 fcntl.fcntl(fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC, 503, 'key_fd_invalid')
            seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
            need(fcntl.fcntl(fd, fcntl.F_GET_SEALS) & seals == seals and
                 os.readlink('/proc/self/fd/' + str(fd)) == '/memfd:rr-project-browser-key (deleted)',
                 503, 'key_fd_invalid')
            value = os.pread(fd, 65, 0)
            need(len(value) == info.st_size, 503, 'key_fd_invalid')
            return value
    finally:
        for fd in received:
            os.close(fd)


class NativeKey:
    name = KEY_NAME

    def __init__(self):
        need(os.getuid() == OWNER_UID, 503, 'owner_required')
        self._value = receive_key()

    def value(self):
        need(hmac.compare_digest(receive_key(), self._value), 503, 'key_supply_changed')
        return self._value

    def close(self):
        self._value = b''
