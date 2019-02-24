import base64

from Crypto import Random
from Crypto.Cipher import AES

from django.conf import settings


class AESCipher(object):
    def __init__(self):
        self.blocksize = 16
        self.key = base64.b64decode(
            getattr(settings, 'AES_SHARED_KEY').encode())

    def encrypt(self, raw):
        raw = self._pad(raw)
        # iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key)
        return base64.b64encode(cipher.encrypt(raw))

    def decrypt(self, encrypted):
        encrypted = base64.b64decode(encrypted)
        iv = encrypted[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(
            encrypted[AES.block_size:])).decode('utf-8')

    def _pad(self, string):
        bs = self.blocksize
        return string + (bs - len(string) % bs) * chr(bs - len(string) % bs)

    @staticmethod
    def _unpad(string):
        return string[:-ord(string[len(string) - 1:])]
