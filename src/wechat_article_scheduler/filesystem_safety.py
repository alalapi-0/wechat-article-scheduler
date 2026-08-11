"""Race-resistant local filesystem primitives for project-managed files."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import os
from pathlib import Path
import stat
from typing import Iterator, Iterable
import uuid


MAX_DIRECTORY_ENTRIES = 10_000
_ENTRY_READ_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
)
_DIRECTORY_FLAGS = _ENTRY_READ_FLAGS | getattr(os, "O_DIRECTORY", 0)


class UnsafePathError(ValueError):
    pass


@dataclass(frozen=True)
class FileSnapshot:
    data: bytes
    device: int
    inode: int


def _validate_entry_name(name: str) -> str:
    if (
        not isinstance(name, str)
        or not name
        or name in {".", ".."}
        or "\x00" in name
        or Path(name).name != name
    ):
        raise UnsafePathError("目录项名称无效")
    return name


def _read_all(fd: int, *, max_bytes: int | None = None) -> bytes:
    if max_bytes is not None and max_bytes < 0:
        raise ValueError("max_bytes 不能为负数")
    info = os.fstat(fd)
    if max_bytes is not None and info.st_size > max_bytes:
        raise UnsafePathError("文件超过允许大小")
    chunks: list[bytes] = []
    total = 0
    while True:
        read_size = 1024 * 1024
        if max_bytes is not None:
            read_size = min(read_size, max_bytes + 1 - total)
        chunk = os.read(fd, read_size)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if max_bytes is not None and total > max_bytes:
            raise UnsafePathError("文件超过允许大小")
        chunks.append(chunk)


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def is_under(path: Path, roots: Iterable[Path]) -> bool:
    candidate = _absolute(path)
    return any(_relative(candidate, _absolute(root)) is not None for root in roots)


def _relative(path: Path, root: Path) -> Path | None:
    try:
        return path.relative_to(root)
    except ValueError:
        return None


def _require_allowed(path: Path, roots: Iterable[Path]) -> Path:
    absolute = _absolute(path)
    if not is_under(absolute, roots):
        raise UnsafePathError("路径不在允许目录中")
    return absolute


def _open_directory(path: Path, *, create: bool, roots: Iterable[Path]) -> int:
    absolute = _require_allowed(path, roots)
    flags = _DIRECTORY_FLAGS
    fd = os.open(absolute.anchor, flags)
    try:
        for part in absolute.parts[1:]:
            try:
                next_fd = os.open(part, flags, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, 0o700, dir_fd=fd)
                next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except OSError as exc:
        os.close(fd)
        raise UnsafePathError("目录路径不存在或包含符号链接") from exc
    except BaseException:
        os.close(fd)
        raise


class DirectoryHandle:
    """An exact, no-follow directory identity held for a complete list/use operation."""

    def __init__(self, path: Path, fd: int):
        self.path = _absolute(path)
        self._fd = fd

    @property
    def closed(self) -> bool:
        return self._fd < 0

    def close(self) -> None:
        if not self.closed:
            os.close(self._fd)
            self._fd = -1

    def __enter__(self) -> DirectoryHandle:
        if self.closed:
            raise UnsafePathError("目录句柄已关闭")
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def list_names(self, *, max_entries: int = MAX_DIRECTORY_ENTRIES) -> list[str]:
        if self.closed:
            raise UnsafePathError("目录句柄已关闭")
        if max_entries < 0:
            raise ValueError("max_entries 不能为负数")
        names: list[str] = []
        try:
            with os.scandir(self._fd) as entries:
                for entry in entries:
                    if len(names) >= max_entries:
                        raise UnsafePathError("目录项数量超过安全上限")
                    names.append(_validate_entry_name(entry.name))
        except UnsafePathError:
            raise
        except OSError as exc:
            raise UnsafePathError("目录无法安全遍历") from exc
        return sorted(names)

    def read_regular_file(
        self,
        name: str,
        *,
        single_link: bool = True,
        max_bytes: int | None = None,
    ) -> FileSnapshot:
        name = _validate_entry_name(name)
        if self.closed:
            raise UnsafePathError("目录句柄已关闭")
        try:
            fd = os.open(name, _ENTRY_READ_FLAGS, dir_fd=self._fd)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or (single_link and info.st_nlink != 1):
                    raise UnsafePathError("文件类型或链接状态无效")
                named = os.stat(name, dir_fd=self._fd, follow_symlinks=False)
                if (named.st_dev, named.st_ino) != (info.st_dev, info.st_ino):
                    raise UnsafePathError("目录项在读取期间发生变化")
                return FileSnapshot(
                    _read_all(fd, max_bytes=max_bytes),
                    info.st_dev,
                    info.st_ino,
                )
            finally:
                os.close(fd)
        except UnsafePathError:
            raise
        except OSError as exc:
            raise UnsafePathError("文件无法安全读取") from exc

    @contextmanager
    def open_child_directory(self, name: str) -> Iterator[DirectoryHandle]:
        name = _validate_entry_name(name)
        if self.closed:
            raise UnsafePathError("目录句柄已关闭")
        flags = _DIRECTORY_FLAGS
        try:
            child_fd = os.open(name, flags, dir_fd=self._fd)
        except OSError as exc:
            raise UnsafePathError("子目录不存在或不安全") from exc
        child = DirectoryHandle(self.path / name, child_fd)
        try:
            yield child
        finally:
            child.close()

    def unlink_if_unchanged(self, name: str, snapshot: FileSnapshot) -> bool:
        name = _validate_entry_name(name)
        if self.closed:
            raise UnsafePathError("目录句柄已关闭")
        return _unlink_entry_if_unchanged(self._fd, name, snapshot)


@contextmanager
def open_directory_handle(
    directory: Path,
    *,
    allowed_roots: Iterable[Path],
    create: bool = False,
) -> Iterator[DirectoryHandle]:
    """Keep the validated directory fd alive until all listed entries are consumed."""
    absolute = _require_allowed(directory, allowed_roots)
    handle = DirectoryHandle(
        absolute,
        _open_directory(absolute, create=create, roots=allowed_roots),
    )
    try:
        yield handle
    finally:
        handle.close()


def read_regular_file(
    path: Path,
    *,
    allowed_roots: Iterable[Path],
    single_link: bool = True,
    max_bytes: int | None = None,
) -> FileSnapshot:
    absolute = _require_allowed(path, allowed_roots)
    parent_fd = _open_directory(absolute.parent, create=False, roots=allowed_roots)
    try:
        fd = os.open(absolute.name, _ENTRY_READ_FLAGS, dir_fd=parent_fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or (single_link and info.st_nlink != 1):
                raise UnsafePathError("文件类型或链接状态无效")
            return FileSnapshot(
                _read_all(fd, max_bytes=max_bytes),
                info.st_dev,
                info.st_ino,
            )
        finally:
            os.close(fd)
    except OSError as exc:
        raise UnsafePathError("文件无法安全读取") from exc
    finally:
        os.close(parent_fd)


def write_unique_file(
    directory: Path,
    filename: str,
    data: bytes,
    *,
    allowed_roots: Iterable[Path],
) -> Path:
    absolute = _require_allowed(directory, allowed_roots)
    dir_fd = _open_directory(absolute, create=True, roots=allowed_roots)
    base = Path(filename).name
    stem, suffix = Path(base).stem, Path(base).suffix
    try:
        for index in range(10000):
            name = base if index == 0 else f"{stem}_{index}{suffix}"
            try:
                fd = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                    dir_fd=dir_fd,
                )
            except FileExistsError:
                continue
            try:
                view = memoryview(data)
                while view:
                    view = view[os.write(fd, view) :]
                os.fsync(fd)
            except BaseException:
                os.close(fd)
                os.unlink(name, dir_fd=dir_fd)
                raise
            else:
                os.close(fd)
            if not _written_file_is_safe(dir_fd, name, data):
                try:
                    os.unlink(name, dir_fd=dir_fd)
                except OSError:
                    pass
                raise UnsafePathError("新文件写入后出现别名或内容变化")
            return absolute / name
    finally:
        os.close(dir_fd)
    raise UnsafePathError("无法分配安全文件名")


def write_new_file(
    path: Path, data: bytes, *, allowed_roots: Iterable[Path]
) -> Path:
    absolute = _require_allowed(path, allowed_roots)
    parent_fd = _open_directory(absolute.parent, create=True, roots=allowed_roots)
    try:
        try:
            fd = os.open(
                absolute.name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=parent_fd,
            )
        except OSError as exc:
            raise UnsafePathError("目标文件已存在或不安全") from exc
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(fd, view) :]
            os.fsync(fd)
        except BaseException:
            os.close(fd)
            os.unlink(absolute.name, dir_fd=parent_fd)
            raise
        else:
            os.close(fd)
        if not _written_file_is_safe(parent_fd, absolute.name, data):
            try:
                os.unlink(absolute.name, dir_fd=parent_fd)
            except OSError:
                pass
            raise UnsafePathError("新文件写入后出现别名或内容变化")
        return absolute
    finally:
        os.close(parent_fd)


def ensure_directory(directory: Path, *, allowed_roots: Iterable[Path]) -> Path:
    absolute = _require_allowed(directory, allowed_roots)
    fd = _open_directory(absolute, create=True, roots=allowed_roots)
    os.close(fd)
    return absolute


def safe_directory_exists(directory: Path, *, allowed_roots: Iterable[Path]) -> bool:
    try:
        fd = _open_directory(directory, create=False, roots=allowed_roots)
    except (OSError, UnsafePathError):
        return False
    os.close(fd)
    return True


def list_directory_names(directory: Path, *, allowed_roots: Iterable[Path]) -> list[str]:
    """Compatibility helper for callers that only count names and never reopen entries."""
    with open_directory_handle(directory, allowed_roots=allowed_roots) as handle:
        return handle.list_names()


def path_chain_is_unaliased(path: Path) -> bool:
    """Return false if any existing component is a symlink or non-directory parent."""
    absolute = _absolute(path)
    current = Path(absolute.anchor)
    try:
        for part in absolute.parts[1:]:
            current = current / part
            try:
                info = os.lstat(current)
            except FileNotFoundError:
                return True
            if stat.S_ISLNK(info.st_mode):
                return False
            if current != absolute and not stat.S_ISDIR(info.st_mode):
                return False
        return True
    except (OSError, UnsafePathError):
        return False


def unlink_if_unchanged(
    path: Path,
    snapshot: FileSnapshot,
    *,
    allowed_roots: Iterable[Path],
) -> bool:
    absolute = _require_allowed(path, allowed_roots)
    parent_fd = _open_directory(absolute.parent, create=False, roots=allowed_roots)
    try:
        return _unlink_entry_if_unchanged(parent_fd, absolute.name, snapshot)
    finally:
        os.close(parent_fd)


def _unlink_entry_if_unchanged(parent_fd: int, name: str, snapshot: FileSnapshot) -> bool:
    # A different UID must not be able to replace the name between verification and
    # quarantine. Processes running as this UID (and root) remain outside the local
    # trust boundary because POSIX offers no atomic compare-and-unlink primitive.
    try:
        parent = os.fstat(parent_fd)
        if (
            not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid != os.geteuid()
            or stat.S_IMODE(parent.st_mode) & 0o022
        ):
            return False
    except OSError:
        return False
    try:
        fd = os.open(
            name,
            _ENTRY_READ_FLAGS,
            dir_fd=parent_fd,
        )
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or (info.st_dev, info.st_ino) != (snapshot.device, snapshot.inode)
                or _read_all(fd) != snapshot.data
            ):
                return False
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (named.st_dev, named.st_ino) != (info.st_dev, info.st_ino):
                return False
            quarantine_fd, quarantine_entry = _quarantine_entry(parent_fd, name)
            try:
                try:
                    moved_fd = os.open(
                        quarantine_entry,
                        _ENTRY_READ_FLAGS,
                        dir_fd=quarantine_fd,
                    )
                    try:
                        moved = os.fstat(moved_fd)
                        matches = (
                            stat.S_ISREG(moved.st_mode)
                            and moved.st_nlink == 1
                            and (moved.st_dev, moved.st_ino) == (snapshot.device, snapshot.inode)
                            and _read_all(moved_fd) == snapshot.data
                        )
                        disposed = False
                        if matches:
                            disposed = _unlink_verified_quarantine(
                                quarantine_fd,
                                quarantine_entry,
                                moved_fd,
                                snapshot,
                            )
                    finally:
                        os.close(moved_fd)
                except (OSError, UnsafePathError):
                    disposed = False
                if disposed:
                    return True
                _restore_quarantined_entry(parent_fd, quarantine_fd, quarantine_entry, name)
                return False
            finally:
                os.close(quarantine_fd)
        finally:
            os.close(fd)
    except (OSError, UnsafePathError):
        return False


def _unlink_verified_quarantine(
    quarantine_fd: int,
    entry: str,
    moved_fd: int,
    snapshot: FileSnapshot,
) -> bool:
    """Delete only while the validated inode and its private name stay bound.

    POSIX has no compare-and-unlink operation, so the random quarantine name is the
    private namespace and the open descriptor is retained through the syscall.  A
    final identity check immediately precedes unlink, and the postcondition proves
    that the held inode lost its only link.  Any identity loss visible at the
    boundary fails closed and is rolled back by the caller.
    """
    try:
        named = os.stat(entry, dir_fd=quarantine_fd, follow_symlinks=False)
        held = os.fstat(moved_fd)
        if (
            not stat.S_ISREG(held.st_mode)
            or held.st_nlink != 1
            or (held.st_dev, held.st_ino) != (snapshot.device, snapshot.inode)
            or (named.st_dev, named.st_ino) != (held.st_dev, held.st_ino)
        ):
            return False
        os.unlink(entry, dir_fd=quarantine_fd)
        disposed = os.fstat(moved_fd)
        return disposed.st_nlink == 0
    except OSError:
        return False


_QUARANTINE_DIRECTORY = ".delete-quarantine"


def _open_owned_quarantine(parent_fd: int) -> int:
    """Open and pin the app-owned private quarantine directory.

    The owner/mode checks exclude replacement by a different unprivileged UID.
    A process running as the same UID (or root) can still race POSIX directory
    operations and is outside this local trust boundary.
    """
    created_identity: tuple[int, int] | None = None
    try:
        os.mkdir(_QUARANTINE_DIRECTORY, 0o700, dir_fd=parent_fd)
        created = os.stat(
            _QUARANTINE_DIRECTORY,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        created_identity = (created.st_dev, created.st_ino)
    except FileExistsError:
        pass
    flags = _DIRECTORY_FLAGS
    quarantine_fd = os.open(_QUARANTINE_DIRECTORY, flags, dir_fd=parent_fd)
    try:
        held = os.fstat(quarantine_fd)
        named = os.stat(_QUARANTINE_DIRECTORY, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(held.st_mode)
            or stat.S_IMODE(held.st_mode) != 0o700
            or held.st_uid != os.geteuid()
            or (held.st_dev, held.st_ino) != (named.st_dev, named.st_ino)
            or (
                created_identity is not None
                and (held.st_dev, held.st_ino) != created_identity
            )
        ):
            raise UnsafePathError("删除隔离目录身份或权限无效")
    except BaseException:
        os.close(quarantine_fd)
        raise
    return quarantine_fd


def _quarantine_entry(parent_fd: int, name: str) -> tuple[int, str]:
    """Move an entry under a pinned private directory without a known collision."""
    quarantine_fd = _open_owned_quarantine(parent_fd)
    try:
        for _ in range(128):
            entry = f"entry-{uuid.uuid4().hex}"
            try:
                os.stat(entry, dir_fd=quarantine_fd, follow_symlinks=False)
            except FileNotFoundError:
                # The directory is mode 0700 and owned by this process' UID.  Thus a
                # different-UID parent writer cannot create a collision after this
                # check even if it renames/replaces the parent-level directory name.
                os.rename(name, entry, src_dir_fd=parent_fd, dst_dir_fd=quarantine_fd)
                return quarantine_fd, entry
        raise UnsafePathError("无法分配删除隔离名称")
    except BaseException:
        os.close(quarantine_fd)
        raise


def _restore_quarantined_entry(
    parent_fd: int,
    quarantine_fd: int,
    entry: str,
    name: str,
) -> None:
    """Restore without overwrite from the private quarantine namespace."""
    try:
        os.link(
            entry,
            name,
            src_dir_fd=quarantine_fd,
            dst_dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except OSError:
        return
    try:
        os.unlink(entry, dir_fd=quarantine_fd)
    except OSError:
        pass


def _written_file_is_safe(parent_fd: int, name: str, expected: bytes) -> bool:
    try:
        fd = os.open(name, _ENTRY_READ_FLAGS, dir_fd=parent_fd)
        try:
            info = os.fstat(fd)
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            return (
                stat.S_ISREG(info.st_mode)
                and info.st_nlink == 1
                and (info.st_dev, info.st_ino) == (named.st_dev, named.st_ino)
                and _read_all(fd) == expected
            )
        finally:
            os.close(fd)
    except OSError:
        return False


def move_regular_file(
    source: Path,
    destination_dir: Path,
    *,
    source_roots: Iterable[Path],
    destination_roots: Iterable[Path],
) -> Path:
    snapshot = read_regular_file(source, allowed_roots=source_roots)
    destination = write_unique_file(
        destination_dir,
        source.name,
        snapshot.data,
        allowed_roots=destination_roots,
    )
    if not unlink_if_unchanged(source, snapshot, allowed_roots=source_roots):
        try:
            created = read_regular_file(destination, allowed_roots=destination_roots)
            unlink_if_unchanged(destination, created, allowed_roots=destination_roots)
        except UnsafePathError:
            pass
        raise UnsafePathError("源文件在移动期间发生变化")
    return destination


def move_file_snapshot(
    source: Path,
    destination_dir: Path,
    snapshot: FileSnapshot,
    *,
    source_roots: Iterable[Path],
    destination_roots: Iterable[Path],
    source_directory: DirectoryHandle | None = None,
) -> Path:
    destination = write_unique_file(
        destination_dir,
        source.name,
        snapshot.data,
        allowed_roots=destination_roots,
    )
    removed = (
        source_directory.unlink_if_unchanged(source.name, snapshot)
        if source_directory is not None
        else unlink_if_unchanged(source, snapshot, allowed_roots=source_roots)
    )
    if removed:
        return destination
    try:
        created = read_regular_file(destination, allowed_roots=destination_roots)
        unlink_if_unchanged(destination, created, allowed_roots=destination_roots)
    except UnsafePathError:
        pass
    raise UnsafePathError("源文件在移动期间发生变化")
