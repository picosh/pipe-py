# Import required libraries
from typing import List, Optional, AnyStr, Callable
import shlex  # For shell-safe command argument parsing
import asyncssh  # For SSH client functionality


class PipeBase:
    """Base class for SSH pipe communication handling both input and output streams."""

    # Type hints for class attributes
    _proc: asyncssh.SSHClientProcess  # The SSH process
    _input: asyncssh.SSHWriter  # stdin writer
    _output: asyncssh.SSHReader  # stdout reader

    def __init__(self, proc: asyncssh.SSHClientProcess) -> None:
        """Initialize the pipe with an SSH process."""
        self._proc = proc
        self._input = proc.stdin
        self._output = proc.stdout

    async def close(self) -> None:
        """Close the SSH process and its streams."""
        return await self._proc.close()


class Sub(PipeBase):
    """Implements read operations for receiving data through SSH."""

    def read_done(self) -> bool:
        """Check if we've reached the end of the output stream."""
        return self._output.at_eof()

    async def read(self, size: int = 32 * 1024) -> AnyStr:
        """Read data from the output stream."""
        return await self._output.read(size)


class Pub(PipeBase):
    """Implements write operations for sending data through SSH."""

    def write_done(self) -> bool:
        """Check if the input stream is closing."""
        return self._input.is_closing()

    async def write(self, data: AnyStr) -> None:
        """Write data to the input stream and ensure it's sent."""
        self._input.write(data)
        return await self._input.drain()


class Pipe(Sub, Pub):
    """Combines Subscriber and Publisher capabilities for bidirectional communication."""

    pass


class PipeClient:
    """Main client class for managing SSH connections and creating pipes."""

    # SSH connection parameters with type annotations
    remote_host: str
    remote_port: Optional[int]
    key_location: Optional[str]
    key_passphrase: Optional[str]
    remote_user: str

    # SSH client connection instance
    client: Optional[asyncssh.SSHClientConnection]

    def __init__(
        self,
        remote_host: str,
        remote_port: Optional[int] = None,
        key_location: Optional[str] = None,
        key_passphrase: Optional[str] = None,
        remote_user: str = "",
    ) -> None:
        """Initialize the SSH pipe client."""
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.key_location = key_location
        self.key_passphrase = key_passphrase
        self.remote_user = remote_user
        self.client = None

    async def open(self) -> None:
        """Establish SSH connection with the configured parameters."""
        self.client = await asyncssh.connect(
            self.remote_host,
            self.remote_port,
            options=asyncssh.SSHClientConnectionOptions(
                known_hosts=None,  # Skip known hosts verification
                username=self.remote_user,
                client_keys=[self.key_location] if self.key_location else None,
                passphrase=self.key_passphrase,
            ),
        )

    async def close(self) -> None:
        """Close the SSH connection if it exists."""
        if self.client is None:
            return
        self.client.close()

    async def pipe(
        self, topic: str = "", public: bool = False, replay: bool = False
    ) -> Pipe:
        """Create a bidirectional pipe for both reading and writing."""
        if self.client is None:
            await self.open()

        # Build command arguments
        args: List[str] = ["pipe"]
        if topic:
            args.append(topic)
        if public:
            args.append("-p")
        if replay:
            args.append("-r")

        return Pipe(await self.client.create_process(shlex.join(args)))

    async def pub(
        self,
        topic: str = "",
        block: bool = True,
        empty: bool = False,
        public: bool = False,
        timeout: str = "",
    ) -> Pub:
        """Create a publisher pipe for writing data."""
        if self.client is None:
            await self.open()

        # Build command arguments
        args: List[str] = ["pub"]
        if topic:
            args.append(topic)
        if not block:
            args.append("-b=false")
        if empty:
            args.append("-e")
        if public:
            args.append("-p")
        if timeout:
            args.append(f"-t={timeout}")

        return Pub(await self.client.create_process(shlex.join(args)))

    async def sub(self, topic: str, keep: bool = False, public: bool = False) -> Sub:
        """Create a subscriber pipe for reading data."""
        if self.client is None:
            await self.open()

        # Build command arguments
        args: List[str] = ["sub", topic]
        if keep:
            args.append("-k")
        if public:
            args.append("-p")

        return Sub(await self.client.create_process(shlex.join(args)))
