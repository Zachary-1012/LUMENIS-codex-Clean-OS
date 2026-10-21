"""Per-process synthetic-test guard. Never a product/runtime configuration."""
import ipaddress
import os
import sys

def _loopback(value):
    if value is None:
        return False
    if isinstance(value, bytes):
        value = value.decode('ascii', errors='strict')
    if str(value).lower().rstrip('.') == 'localhost':
        return True
    try:
        return ipaddress.ip_address(str(value).split('%', 1)[0]).is_loopback
    except ValueError:
        return False

def _deny_address(address):
    # UNIX sockets are local IPC; internet sockets must be literal loopback.
    if isinstance(address, tuple) and not _loopback(address[0]):
        raise PermissionError('SYNTHETIC_TEST_NON_LOOPBACK_DENIED')

def _audit(event, args):
    if event in ('socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyaddr'):
        if not _loopback(args[0]):
            raise PermissionError('SYNTHETIC_TEST_DNS_DENIED')
    elif event in ('socket.connect', 'socket.bind'):
        _deny_address(args[1])
    elif event == 'socket.sendto':
        _deny_address(args[-1])
    elif event == 'import' and args[0].split('.')[0] == 'onnxruntime' and os.environ.get('ORT_DISABLE_TELEMETRY') != '1':
        # Native C telemetry is not covered by CPython socket audit events.
        # Do not claim Python-only network guards contain that runtime.
        raise ImportError('SYNTHETIC_TEST_NATIVE_ONNX_RUNTIME_NOT_ADMITTED')

sys.addaudithook(_audit)
os.environ['ZBC_ALLOW_NETWORK'] = '0'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

# socket.connect resolves a hostname in C before emitting its connect event.
# Reject hostnames before entering that resolver as well as at audit time.
import socket
_original_socket = socket.socket
class LoopbackOnlySocket(_original_socket):
    def connect(self, address):
        _deny_address(address)
        return super().connect(address)
    def connect_ex(self, address):
        _deny_address(address)
        return super().connect_ex(address)
    def sendto(self, *args):
        _deny_address(args[-1])
        return super().sendto(*args)
socket.socket = LoopbackOnlySocket
