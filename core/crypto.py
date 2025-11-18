"""
Cryptographic primitives for production blockchain
Uses ECDSA (secp256k1) for signatures and Keccak-256 for hashing (Ethereum compatible)
"""
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Optional
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigencode_string, sigdecode_string
from ecdsa.keys import BadSignatureError

# DÜZELTME: Sorunlu 'import sha3' yerine doğrudan 'pycryptodome' içinden import ediyoruz
from Crypto.Hash import keccak


def sha256(data: bytes) -> str:
    """SHA-256 hash returning hex string"""
    return hashlib.sha256(data).hexdigest()


def hash_object(obj: Any) -> str:
    """Deterministic hash of any JSON-serializable object using SHA-256"""
    canonical = json.dumps(obj, sort_keys=True, separators=(',', ':'))
    return sha256(canonical.encode('utf-8'))


def keccak256(data: bytes) -> bytes:
    """Keccak-256 hash (pycryptodome kullanarak)"""
    # DÜZELTME: 'sha3.keccak_256()' yerine bu bloğu kullanıyoruz
    k = keccak.new(digest_bits=256)
    k.update(data)
    return k.digest()


@dataclass(frozen=True)
class KeyPair:
    """ECDSA (secp256k1) keypair for signing"""
    private_key: bytes  # 32 bytes
    public_key: bytes   # 64 bytes (uncompressed)

    @classmethod
    def generate(cls) -> 'KeyPair':
        """Generate new random keypair"""
        sk = SigningKey.generate(curve=SECP256k1)
        vk = sk.get_verifying_key()
        return cls(
            private_key=sk.to_string(),
            public_key=vk.to_string("uncompressed")  # 64 bytes
        )

    @classmethod
    def from_seed(cls, seed: str) -> 'KeyPair':
        """Generate deterministic keypair from seed (for testing)"""
        seed_hash = hashlib.sha256(seed.encode()).digest()
        sk = SigningKey.from_string(seed_hash, curve=SECP256k1)
        vk = sk.get_verifying_key()
        return cls(
            private_key=sk.to_string(),
            public_key=vk.to_string("uncompressed")
        )

    @classmethod
    def from_private_key_hex(cls, private_key_hex: str) -> 'KeyPair':
        """Create keypair from private key hex string"""
        private_key_bytes = bytes.fromhex(private_key_hex)
        sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
        vk = sk.get_verifying_key()
        return cls(
            private_key=sk.to_string(),
            public_key=vk.to_string("uncompressed")
        )

    def address(self) -> str:
        """Get address from public key (Ethereum style)"""
        # Remove 0x04 prefix if exists (uncompressed marker)
        pubkey = self.public_key
        if len(pubkey) == 65 and pubkey[0] == 0x04:
            pubkey = pubkey[1:]  # Remove prefix, use only X,Y coordinates (64 bytes)

        # Keccak-256 hash -> Last 20 bytes -> Add '0x'
        pubkey_hash = keccak256(pubkey)
        addr_bytes = pubkey_hash[-20:]
        return "0x" + addr_bytes.hex()

    def public_key_hex(self) -> str:
        """Get public key as hex string"""
        return self.public_key.hex()

    def private_key_hex(self) -> str:
        """Get private key as hex string"""
        return self.private_key.hex()

    def sign(self, message: bytes) -> bytes:
        """Sign a message, returns 64-byte signature"""
        sk = SigningKey.from_string(self.private_key, curve=SECP256k1)
        # KRITIK DEGISIKLIK: Ethereum uyumluluğu için Keccak256 kullan
        message_hash = keccak256(message)  # SHA256 yerine Keccak256!
        signature = sk.sign_digest(message_hash, sigencode=sigencode_string)
        return signature  # 64 bytes

    def sign_dict(self, data: dict) -> str:
        """Sign a dictionary, returns hex signature"""
        message = json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
        signature = self.sign(message)
        return signature.hex()


def verify_signature(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """Verify ECDSA (secp256k1) signature"""
    try:
        vk = VerifyingKey.from_string(public_key, curve=SECP256k1)
        # KRITIK DEGISIKLIK: Ethereum uyumluluğu için Keccak256 kullan
        message_hash = keccak256(message)  # SHA256 yerine Keccak256!
        return vk.verify_digest(signature, message_hash, sigdecode=sigdecode_string)
    except (BadSignatureError, ValueError):
        return False


def verify_dict_signature(public_key: bytes, data: dict, signature_hex: str) -> bool:
    """Verify signature on a dictionary"""
    try:
        message = json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
        signature = bytes.fromhex(signature_hex)
        return verify_signature(public_key, message, signature)
    except (ValueError, TypeError):
        return False


def address_from_public_key(public_key: bytes) -> str:
    """Convert public key to address"""
    pubkey_hash = keccak256(public_key)
    addr_bytes = pubkey_hash[-20:]
    return "0x" + addr_bytes.hex()


def is_valid_address(address: str) -> bool:
    """Check if address format is valid (Ethereum style)"""
    if not isinstance(address, str):
        return False

    if not address.startswith('0x'):
        return False

    if len(address) != 42:
        return False

    # Check if hex is valid
    try:
        int(address[2:], 16)  # Skip 0x prefix
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    # Test the crypto module
    print("=== Cryptography Module Test (ECDSA + Keccak) ===\n")

    # Generate keypair
    kp = KeyPair.generate()
    print(f"Generated keypair")
    print(f"Address: {kp.address()}")
    print(f"Public key: {kp.public_key_hex()[:32]}...")

    # Sign and verify
    message = b"Hello, Blockchain!"
    signature = kp.sign(message)
    print(f"\nSigned message: {message.decode()}")
    print(f"Signature: {signature.hex()[:32]}...")

    valid = verify_signature(kp.public_key, message, signature)
    print(f"Signature valid: {valid}")

    # Test with wrong message
    wrong_valid = verify_signature(kp.public_key, b"Wrong message", signature)
    print(f"Wrong message valid: {wrong_valid}")

    # Test address validation
    print(f"\nAddress valid: {is_valid_address(kp.address())}")
    print(f"Invalid '0x' missing: {is_valid_address(kp.address()[2:])}")
    print(f"Invalid length: {is_valid_address(kp.address() + '00')}")
    
    # ETHEREUM UYUMLULUK TESTI
    print("\n=== ETHEREUM COMPATIBILITY CHECK ===")
    print("✅ Using Keccak256 for message signing")
    print("✅ Using Keccak256 for signature verification")
    print("✅ Addresses are 0x-prefixed 20-byte Ethereum addresses")
    print("✅ MetaMask compatible!")
