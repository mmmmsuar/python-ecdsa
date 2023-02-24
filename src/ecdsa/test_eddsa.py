import pickle
import hashlib
import pytest

try:
    import unittest2 as unittest
except ImportError:
    import unittest
from hypothesis import given, settings, example
import hypothesis.strategies as st
from .ellipticcurve import PointEdwards, INFINITY, CurveEdTw
from .eddsa import (
    generator_ed25519,
    curve_ed25519,
    generator_ed448,
    curve_ed448,
    PrivateKey,
    PublicKey,
)
from .ecdsa import generator_256, curve_256
from .errors import MalformedPointError
from ._compat import a2b_hex, compat26_str


class TestA2B_Hex(unittest.TestCase):
    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            a2b_hex("abcdefghi")


def test_ed25519_curve_compare():
    assert curve_ed25519 != curve_256


def test_ed25519_and_ed448_compare():
    assert curve_ed448 != curve_ed25519


def test_ed25519_and_custom_curve_compare():
    a = CurveEdTw(curve_ed25519.p(), -curve_ed25519.a(), 1)

    assert curve_ed25519 != a


def test_ed25519_and_almost_exact_curve_compare():
    a = CurveEdTw(curve_ed25519.p(), curve_ed25519.a(), 1)

    assert curve_ed25519 != a


def test_ed25519_and_same_curve_params():
    a = CurveEdTw(curve_ed25519.p(), curve_ed25519.a(), curve_ed25519.d())

    assert curve_ed25519 == a
    assert not (curve_ed25519 != a)


def test_ed25519_contains_point():
    g = generator_ed25519
    assert curve_ed25519.contains_point(g.x(), g.y())


def test_ed25519_contains_point_bad():
    assert not curve_ed25519.contains_point(1, 1)


def test_ed25519_double():
    a = generator_ed25519

    z = a.double()

    assert isinstance(z, PointEdwards)

    x2 = int(
        "24727413235106541002554574571675588834622768167397638456726423"
        "682521233608206"
    )
    y2 = int(
        "15549675580280190176352668710449542251549572066445060580507079"
        "593062643049417"
    )

    b = PointEdwards(curve_ed25519, x2, y2, 1, x2 * y2)

    assert z == b
    assert a != b


def test_ed25519_add_as_double():
    a = generator_ed25519

    z = a + a

    assert isinstance(z, PointEdwards)

    b = generator_ed25519.double()

    assert z == b


def test_ed25519_double_infinity():
    a = PointEdwards(curve_ed25519, 0, 1, 1, 0)

    z = a.double()

    assert z is INFINITY


def test_ed25519_double_badly_encoded_infinity():
    # invalid point, mostly to make instrumental happy
    a = PointEdwards(curve_ed25519, 1, 1, 1, 0)

    z = a.double()

    assert z is INFINITY


def test_ed25519_eq_with_different_z():
    x = generator_ed25519.x()
    y = generator_ed25519.y()
    p = curve_ed25519.p()

    a = PointEdwards(curve_ed25519, x * 2 % p, y * 2 % p, 2, x * y * 2 % p)
    b = PointEdwards(curve_ed25519, x * 3 % p, y * 3 % p, 3, x * y * 3 % p)

    assert a == b

    assert not (a != b)


def test_ed25519_eq_against_infinity():
    assert generator_ed25519 != INFINITY


def test_ed25519_eq_encoded_infinity_against_infinity():
    a = PointEdwards(curve_ed25519, 0, 1, 1, 0)
    assert a == INFINITY


def test_ed25519_eq_bad_encode_of_infinity_against_infinity():
    # technically incorrect encoding of the point at infinity, but we check
    # both X and T, so verify that just T==0 works
    a = PointEdwards(curve_ed25519, 1, 1, 1, 0)
    assert a == INFINITY


def test_ed25519_eq_against_non_Edwards_point():
    assert generator_ed25519 != generator_256


def test_ed25519_eq_against_negated_point():
    g = generator_ed25519
    neg = PointEdwards(curve_ed25519, -g.x(), g.y(), 1, -g.x() * g.y())
    assert g != neg


def test_ed25519_eq_x_different_y():
    # not points on the curve, but __eq__ doesn't care
    a = PointEdwards(curve_ed25519, 1, 1, 1, 1)
    b = PointEdwards(curve_ed25519, 1, 2, 1, 2)

    assert a != b


def test_ed25519_test_normalisation_and_scaling():
    x = generator_ed25519.x()
    y = generator_ed25519.y()
    p = curve_ed25519.p()

    a = PointEdwards(curve_ed25519, x * 11 % p, y * 11 % p, 11, x * y * 11 % p)

    assert a.x() == x
    assert a.y() == y

    a.scale()

    assert a.x() == x
    assert a.y() == y

    a.scale()  # second execution should be a noop

    assert a.x() == x
    assert a.y() == y


def test_ed25519_add_three_times():
    a = generator_ed25519

    z = a + a + a

    x3 = int(
        "468967334644549386571235445953867877890461982801326656862413"
        "21779790909858396"
    )
    y3 = int(
        "832484377853344397649037712036920113830141722629755531674120"
        "2210403726505172"
    )

    b = PointEdwards(curve_ed25519, x3, y3, 1, x3 * y3)

    assert z == b


def test_ed25519_add_to_infinity():
    # generator * (order-1)
    x1 = int(
        "427838232691226969392843410947554224151809796397784248136826"
        "78720006717057747"
    )
    y1 = int(
        "463168356949264781694283940034751631413079938662562256157830"
        "33603165251855960"
    )
    inf_m_1 = PointEdwards(curve_ed25519, x1, y1, 1, x1 * y1)

    inf = inf_m_1 + generator_ed25519

    assert inf is INFINITY


def test_ed25519_add_and_mul_equivalence():
    g = generator_ed25519

    assert g + g == g * 2
    assert g + g + g == g * 3


def test_ed25519_add_literal_infinity():
    g = generator_ed25519
    z = g + INFINITY

    assert z == g


def test_ed25519_add_infinity():
    inf = PointEdwards(curve_ed25519, 0, 1, 1, 0)
    g = generator_ed25519
    z = g + inf

    assert z == g

    z = inf + g

    assert z == g


class TestEd25519(unittest.TestCase):
    def test_add_wrong_curves(self):
        with self.assertRaises(ValueError) as e:
            generator_ed25519 + generator_ed448

        self.assertIn("different curve", str(e.exception))

    def test_add_wrong_point_type(self):
        with self.assertRaises(ValueError) as e:
            generator_ed25519 + generator_256

        self.assertIn("different curve", str(e.exception))


def test_ed25519_mul_to_order_min_1():
    x1 = int(
        "427838232691226969392843410947554224151809796397784248136826"
        "78720006717057747"
    )
    y1 = int(
        "463168356949264781694283940034751631413079938662562256157830"
        "33603165251855960"
    )
    inf_m_1 = PointEdwards(curve_ed25519, x1, y1, 1, x1 * y1)

    assert generator_ed25519 * (generator_ed25519.order() - 1) == inf_m_1


def test_ed25519_mul_to_infinity():
    assert generator_ed25519 * generator_ed25519.order() == INFINITY


def test_ed25519_mul_to_infinity_plus_1():
    g = generator_ed25519
    assert g * (g.order() + 1) == g


def test_ed25519_mul_and_add():
    g = generator_ed25519
    a = g * 128
    b = g * 64 + g * 64

    assert a == b


def test_ed25519_mul_and_add_2():
    g = generator_ed25519

    a = g * 123
    b = g * 120 + g * 3

    assert a == b


def test_ed25519_mul_infinity():
    inf = PointEdwards(curve_ed25519, 0, 1, 1, 0)

    z = inf * 11

    assert z == INFINITY


def test_ed25519_mul_by_zero():
    z = generator_ed25519 * 0

    assert z == INFINITY


def test_ed25519_mul_by_one():
    z = generator_ed25519 * 1

    assert z == generator_ed25519


def test_ed25519_mul_custom_point():
    # verify that multiplication without order set works

    g = generator_ed25519

    a = PointEdwards(curve_ed25519, g.x(), g.y(), 1, g.x() * g.y())

    z = a * 11

    assert z == g * 11


def test_ed25519_pickle():
    g = generator_ed25519
    assert pickle.loads(pickle.dumps(g)) == g


def test_ed448_eq_against_different_curve():
    assert generator_ed25519 != generator_ed448


def test_ed448_double():
    g = generator_ed448
    z = g.double()

    assert isinstance(z, PointEdwards)

    x2 = int(
        "4845591495304045936995492052586696895690942404582120401876"
        "6013278705691214670908136440114445572635086627683154494739"
        "7859048262938744149"
    )
    y2 = int(
        "4940887598674337276743026725267350893505445523037277237461"
        "2648447308771911703729389009346215770388834286503647778745"
        "3078312060500281069"
    )

    b = PointEdwards(curve_ed448, x2, y2, 1, x2 * y2)

    assert z == b
    assert g != b


def test_ed448_add_as_double():
    g = generator_ed448
    z = g + g

    b = g.double()

    assert z == b


def test_ed448_mul_as_double():
    g = generator_ed448
    z = g * 2
    b = g.double()

    assert z == b


def test_ed448_add_to_infinity():
    # generator * (order - 1)
    x1 = int(
        "5022586839996825903617194737881084981068517190547539260353"
        "6473749366191269932473977736719082931859264751085238669719"
        "1187378895383117729"
    )
    y1 = int(
        "2988192100784814926760179304439306734375440401540802420959"
        "2824137233150618983587600353687865541878473398230323350346"
        "2500531545062832660"
    )
    inf_m_1 = PointEdwards(curve_ed448, x1, y1, 1, x1 * y1)

    inf = inf_m_1 + generator_ed448

    assert inf is INFINITY


def test_ed448_mul_to_infinity():
    g = generator_ed448
    inf = g * g.order()

    assert inf is INFINITY


def test_ed448_mul_to_infinity_plus_1():
    g = generator_ed448

    z = g * (g.order() + 1)

    assert z == g


def test_ed448_add_and_mul_equivalence():
    g = generator_ed448

    assert g + g == g * 2
    assert g + g + g == g * 3


def test_ed25519_encode():
    g = generator_ed25519
    g_bytes = g.to_bytes()
    assert len(g_bytes) == 32
    exp_bytes = (
        b"\x58\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66"
        b"\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66"
    )
    assert g_bytes == exp_bytes


def test_ed25519_decode():
    exp_bytes = (
        b"\x58\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66"
        b"\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66"
    )
    a = PointEdwards.from_bytes(curve_ed25519, exp_bytes)

    assert a == generator_ed25519


class TestEdwardsMalformed(unittest.TestCase):
    def test_invalid_point(self):
        exp_bytes = (
            b"\x78\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66"
            b"\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66"
        )
        with self.assertRaises(MalformedPointError):
            PointEdwards.from_bytes(curve_ed25519, exp_bytes)

    def test_invalid_length(self):
        exp_bytes = (
            b"\x58\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66"
            b"\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66\x66"
            b"\x66"
        )
        with self.assertRaises(MalformedPointError) as e:
            PointEdwards.from_bytes(curve_ed25519, exp_bytes)

        self.assertIn("length", str(e.exception))

    def test_ed448_invalid(self):
        exp_bytes = b"\xff" * 57
        with self.assertRaises(MalformedPointError):
            PointEdwards.from_bytes(curve_ed448, exp_bytes)


def test_ed448_encode():
    g = generator_ed448
    g_bytes = g.to_bytes()
    assert len(g_bytes) == 57
    exp_bytes = (
        b"\x14\xfa\x30\xf2\x5b\x79\x08\x98\xad\xc8\xd7\x4e\x2c\x13\xbd"
        b"\xfd\xc4\x39\x7c\xe6\x1c\xff\xd3\x3a\xd7\xc2\xa0\x05\x1e\x9c"
        b"\x78\x87\x40\x98\xa3\x6c\x73\x73\xea\x4b\x62\xc7\xc9\x56\x37"
        b"\x20\x76\x88\x24\xbc\xb6\x6e\x71\x46\x3f\x69\x00"
    )
    assert g_bytes == exp_bytes


def test_ed448_decode():
    exp_bytes = (
        b"\x14\xfa\x30\xf2\x5b\x79\x08\x98\xad\xc8\xd7\x4e\x2c\x13\xbd"
        b"\xfd\xc4\x39\x7c\xe6\x1c\xff\xd3\x3a\xd7\xc2\xa0\x05\x1e\x9c"
        b"\x78\x87\x40\x98\xa3\x6c\x73\x73\xea\x4b\x62\xc7\xc9\x56\x37"
        b"\x20\x76\x88\x24\xbc\xb6\x6e\x71\x46\x3f\x69\x00"
    )

    a = PointEdwards.from_bytes(curve_ed448, exp_bytes)

    assert a == generator_ed448


class TestEdDSAEquality(unittest.TestCase):
    def test_equal_public_points(self):
        key1 = PublicKey(generator_ed25519, b"\x01" * 32)
        key2 = PublicKey(generator_ed25519, b"\x01" * 32)

        self.assertEqual(key1, key2)
        # verify that `__ne__` works as expected
        self.assertFalse(key1 != key2)

    def test_unequal_public_points(self):
        key1 = PublicKey(generator_ed25519, b"\x01" * 32)
        key2 = PublicKey(generator_ed25519, b"\x03" * 32)

        self.assertNotEqual(key1, key2)

    def test_unequal_to_string(self):
        key1 = PublicKey(generator_ed25519, b"\x01" * 32)
        key2 = b"\x01" * 32

        self.assertNotEqual(key1, key2)

    def test_unequal_publickey_curves(self):
        key1 = PublicKey(generator_ed25519, b"\x01" * 32)
        key2 = PublicKey(generator_ed448, b"\x03" * 56 + b"\x00")

        self.assertNotEqual(key1, key2)
        # verify that `__ne__` works as expected
        self.assertTrue(key1 != key2)

    def test_equal_private_keys(self):
        key1 = PrivateKey(generator_ed25519, b"\x01" * 32)
        key2 = PrivateKey(generator_ed25519, b"\x01" * 32)

        self.assertEqual(key1, key2)
        # verify that `__ne__` works as expected
        self.assertFalse(key1 != key2)

    def test_unequal_private_keys(self):
        key1 = PrivateKey(generator_ed25519, b"\x01" * 32)
        key2 = PrivateKey(generator_ed25519, b"\x02" * 32)

        self.assertNotEqual(key1, key2)
        # verify that `__ne__` works as expected
        self.assertTrue(key1 != key2)

    def test_unequal_privatekey_to_string(self):
        key1 = PrivateKey(generator_ed25519, b"\x01" * 32)
        key2 = b"\x01" * 32

        self.assertNotEqual(key1, key2)

    def test_unequal_privatekey_curves(self):
        key1 = PrivateKey(generator_ed25519, b"\x01" * 32)
        key2 = PrivateKey(generator_ed448, b"\x01" * 57)

        self.assertNotEqual(key1, key2)


class TestInvalidEdDSAInputs(unittest.TestCase):
    def test_wrong_length_of_private_key(self):
        with self.assertRaises(ValueError):
            PrivateKey(generator_ed25519, b"\x01" * 31)

    def test_wrong_length_of_public_key(self):
        with self.assertRaises(ValueError):
            PublicKey(generator_ed25519, b"\x01" * 33)

    def test_wrong_cofactor_curve(self):
        ed_c = curve_ed25519

        def _hash(data):
            return hashlib.new("sha512", compat26_str(data)).digest()

        curve = CurveEdTw(ed_c.p(), ed_c.a(), ed_c.d(), 1, _hash)
        g = generator_ed25519
        fake_gen = PointEdwards(curve, g.x(), g.y(), 1, g.x() * g.y())

        with self.assertRaises(ValueError) as e:
            PrivateKey(fake_gen, g.to_bytes())

        self.assertIn("cofactor", str(e.exception))

    def test_invalid_signature_length(self):
        key = PublicKey(generator_ed25519, b"\x01" * 32)

        with self.assertRaises(ValueError) as e:
            key.verify(b"", b"\x01" * 65)

        self.assertIn("length", str(e.exception))

    def test_changing_public_key(self):
        key = PublicKey(generator_ed25519, b"\x01" * 32)

        g = key.point

        new_g = PointEdwards(curve_ed25519, g.x(), g.y(), 1, g.x() * g.y())

        key.point = new_g

        self.assertEqual(g, key.point)

    def test_changing_public_key_to_different_point(self):
        key = PublicKey(generator_ed25519, b"\x01" * 32)

        with self.assertRaises(ValueError) as e:
            key.point = generator_ed25519

        self.assertIn("coordinates", str(e.exception))

    def test_invalid_s_value(self):
        key = PublicKey(
            generator_ed25519,
            b"\xd7\x5a\x98\x01\x82\xb1\x0a\xb7\xd5\x4b\xfe\xd3\xc9\x64\x07\x3a"
            b"\x0e\xe1\x72\xf3\xda\xa6\x23\x25\xaf\x02\x1a\x68\xf7\x07\x51\x1a",
        )
        sig_valid = bytearray(
            b"\xe5\x56\x43\x00\xc3\x60\xac\x72\x90\x86\xe2\xcc\x80\x6e\x82\x8a"
            b"\x84\x87\x7f\x1e\xb8\xe5\xd9\x74\xd8\x73\xe0\x65\x22\x49\x01\x55"
            b"\x5f\xb8\x82\x15\x90\xa3\x3b\xac\xc6\x1e\x39\x70\x1c\xf9\xb4\x6b"
            b"\xd2\x5b\xf5\xf0\x59\x5b\xbe\x24\x65\x51\x41\x43\x8e\x7a\x10\x0b"
        )

        self.assertTrue(key.verify(b"", sig_valid))

        sig_invalid = bytearray(sig_valid)
        sig_invalid[-1] = 0xFF

        with self.assertRaises(ValueError):
            key.verify(b"", sig_invalid)

    def test_invalid_r_value(self):
        key = PublicKey(
            generator_ed25519,
            b"\xd7\x5a\x98\x01\x82\xb1\x0a\xb7\xd5\x4b\xfe\xd3\xc9\x64\x07\x3a"
            b"\x0e\xe1\x72\xf3\xda\xa6\x23\x25\xaf\x02\x1a\x68\xf7\x07\x51\x1a",
        )
        sig_valid = bytearray(
            b"\xe5\x56\x43\x00\xc3\x60\xac\x72\x90\x86\xe2\xcc\x80\x6e\x82\x8a"
            b"\x84\x87\x7f\x1e\xb8\xe5\xd9\x74\xd8\x73\xe0\x65\x22\x49\x01\x55"
            b"\x5f\xb8\x82\x15\x90\xa3\x3b\xac\xc6\x1e\x39\x70\x1c\xf9\xb4\x6b"
            b"\xd2\x5b\xf5\xf0\x59\x5b\xbe\x24\x65\x51\x41\x43\x8e\x7a\x10\x0b"
        )

        self.assertTrue(key.verify(b"", sig_valid))

        sig_invalid = bytearray(sig_valid)
        sig_invalid[0] = 0xE0

        with self.assertRaises(ValueError):
            key.verify(b"", sig_invalid)


HYP_SETTINGS = dict()
HYP_SETTINGS["max_examples"] = 10


@settings(**HYP_SETTINGS)
@example(1)
@example(5)  # smallest multiple that requires changing sign of x
@given(st.integers(min_value=1, max_value=int(generator_ed25519.order() - 1)))
def test_ed25519_encode_decode(multiple):
    a = generator_ed25519 * multiple

    b = PointEdwards.from_bytes(curve_ed25519, a.to_bytes())

    assert a == b


@settings(**HYP_SETTINGS)
@example(1)
@example(2)  # smallest multiple that requires changing the sign of x
@given(st.integers(min_value=1, max_value=int(generator_ed448.order() - 1)))
def test_ed448_encode_decode(multiple):
    a = generator_ed448 * multiple

    b = PointEdwards.from_bytes(curve_ed448, a.to_bytes())

    assert a == b


@settings(**HYP_SETTINGS)
@example(1)
@example(2)
@given(st.integers(min_value=1, max_value=int(generator_ed25519.order()) - 1))
def test_ed25519_mul_precompute_vs_naf(multiple):
    """Compare multiplication with and without precomputation."""
    g = generator_ed25519
    new_g = PointEdwards(curve_ed25519, g.x(), g.y(), 1, g.x() * g.y())

    assert g * multiple == multiple * new_g


# Test vectors from RFC 8032
TEST_VECTORS = [
    # TEST 1
    (
        generator_ed25519,
        "9d61b19deffd5a60ba844af492ec2cc4" "4449c5697b326919703bac031cae7f60",
        "d75a980182b10ab7d54bfed3c964073a" "0ee172f3daa62325af021a68f707511a",
        "",
        "e5564300c360ac729086e2cc806e828a"
        "84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46b"
        "d25bf5f0595bbe24655141438e7a100b",
    ),
    # TEST 2
    (
        generator_ed25519,
        "4ccd089b28ff96da9db6c346ec114e0f" "5b8a319f35aba624da8cf6ed4fb8a6fb",
        "3d4017c3e843895a92b70aa74d1b7ebc" "9c982ccf2ec4968cc0cd55f12af4660c",
        "72",
        "92a009a9f0d4cab8720e820b5f642540"
        "a2b27b5416503f8fb3762223ebdb69da"
        "085ac1e43e15996e458f3613d0f11d8c"
        "387b2eaeb4302aeeb00d291612bb0c00",
    ),
    # TEST 3
    (
        generator_ed25519,
        "c5aa8df43f9f837bedb7442f31dcb7b1" "66d38535076f094b85ce3a2e0b4458f7",
        "fc51cd8e6218a1a38da47ed00230f058" "0816ed13ba3303ac5deb911548908025",
        "af82",
        "6291d657deec24024827e69c3abe01a3"
        "0ce548a284743a445e3680d7db5ac3ac"
        "18ff9b538d16f290ae67f760984dc659"
        "4a7c15e9716ed28dc027beceea1ec40a",
    ),
    # TEST 1024
    (
        generator_ed25519,
        "f5e5767cf153319517630f226876b86c" "8160cc583bc013744c6bf255f5cc0ee5",
        "278117fc144c72340f67d0f2316e8386" "ceffbf2b2428c9c51fef7c597f1d426e",
        "08b8b2b733424243760fe426a4b54908"
        "632110a66c2f6591eabd3345e3e4eb98"
        "fa6e264bf09efe12ee50f8f54e9f77b1"
        "e355f6c50544e23fb1433ddf73be84d8"
        "79de7c0046dc4996d9e773f4bc9efe57"
        "38829adb26c81b37c93a1b270b20329d"
        "658675fc6ea534e0810a4432826bf58c"
        "941efb65d57a338bbd2e26640f89ffbc"
        "1a858efcb8550ee3a5e1998bd177e93a"
        "7363c344fe6b199ee5d02e82d522c4fe"
        "ba15452f80288a821a579116ec6dad2b"
        "3b310da903401aa62100ab5d1a36553e"
        "06203b33890cc9b832f79ef80560ccb9"
        "a39ce767967ed628c6ad573cb116dbef"
        "efd75499da96bd68a8a97b928a8bbc10"
        "3b6621fcde2beca1231d206be6cd9ec7"
        "aff6f6c94fcd7204ed3455c68c83f4a4"
        "1da4af2b74ef5c53f1d8ac70bdcb7ed1"
        "85ce81bd84359d44254d95629e9855a9"
        "4a7c1958d1f8ada5d0532ed8a5aa3fb2"
        "d17ba70eb6248e594e1a2297acbbb39d"
        "502f1a8c6eb6f1ce22b3de1a1f40cc24"
        "554119a831a9aad6079cad88425de6bd"
        "e1a9187ebb6092cf67bf2b13fd65f270"
        "88d78b7e883c8759d2c4f5c65adb7553"
        "878ad575f9fad878e80a0c9ba63bcbcc"
        "2732e69485bbc9c90bfbd62481d9089b"
        "eccf80cfe2df16a2cf65bd92dd597b07"
        "07e0917af48bbb75fed413d238f5555a"
        "7a569d80c3414a8d0859dc65a46128ba"
        "b27af87a71314f318c782b23ebfe808b"
        "82b0ce26401d2e22f04d83d1255dc51a"
        "ddd3b75a2b1ae0784504df543af8969b"
        "e3ea7082ff7fc9888c144da2af58429e"
        "c96031dbcad3dad9af0dcbaaaf268cb8"
        "fcffead94f3c7ca495e056a9b47acdb7"
        "51fb73e666c6c655ade8297297d07ad1"
        "ba5e43f1bca32301651339e22904cc8c"
        "42f58c30c04aafdb038dda0847dd988d"
        "cda6f3bfd15c4b4c4525004aa06eeff8"
        "ca61783aacec57fb3d1f92b0fe2fd1a8"
        "5f6724517b65e614ad6808d6f6ee34df"
        "f7310fdc82aebfd904b01e1dc54b2927"
        "094b2db68d6f903b68401adebf5a7e08"
        "d78ff4ef5d63653a65040cf9bfd4aca7"
        "984a74d37145986780fc0b16ac451649"
        "de6188a7dbdf191f64b5fc5e2ab47b57"
        "f7f7276cd419c17a3ca8e1b939ae49e4"
        "88acba6b965610b5480109c8b17b80e1"
        "b7b750dfc7598d5d5011fd2dcc5600a3"
        "2ef5b52a1ecc820e308aa342721aac09"
        "43bf6686b64b2579376504ccc493d97e"
        "6aed3fb0f9cd71a43dd497f01f17c0e2"
        "cb3797aa2a2f256656168e6c496afc5f"
        "b93246f6b1116398a346f1a641f3b041"
        "e989f7914f90cc2c7fff357876e506b5"
        "0d334ba77c225bc307ba537152f3f161"
        "0e4eafe595f6d9d90d11faa933a15ef1"
        "369546868a7f3a45a96768d40fd9d034"
        "12c091c6315cf4fde7cb68606937380d"
        "b2eaaa707b4c4185c32eddcdd306705e"
        "4dc1ffc872eeee475a64dfac86aba41c"
        "0618983f8741c5ef68d3a101e8a3b8ca"
        "c60c905c15fc910840b94c00a0b9d0",
        "0aab4c900501b3e24d7cdf4663326a3a"
        "87df5e4843b2cbdb67cbf6e460fec350"
        "aa5371b1508f9f4528ecea23c436d94b"
        "5e8fcd4f681e30a6ac00a9704a188a03",
    ),
    # TEST SHA(abc)
    (
        generator_ed25519,
        "833fe62409237b9d62ec77587520911e" "9a759cec1d19755b7da901b96dca3d42",
        "ec172b93ad5e563bf4932c70e1245034" "c35467ef2efd4d64ebf819683467e2bf",
        "ddaf35a193617abacc417349ae204131"
        "12e6fa4e89a97ea20a9eeee64b55d39a"
        "2192992a274fc1a836ba3c23a3feebbd"
        "454d4423643ce80e2a9ac94fa54ca49f",
        "dc2a4459e7369633a52b1bf277839a00"
        "201009a3efbf3ecb69bea2186c26b589"
        "09351fc9ac90b3ecfdfbc7c66431e030"
        "3dca179c138ac17ad9bef1177331a704",
    ),
    # Blank
    (
        generator_ed448,
        "6c82a562cb808d10d632be89c8513ebf"
        "6c929f34ddfa8c9f63c9960ef6e348a3"
        "528c8a3fcc2f044e39a3fc5b94492f8f"
        "032e7549a20098f95b",
        "5fd7449b59b461fd2ce787ec616ad46a"
        "1da1342485a70e1f8a0ea75d80e96778"
        "edf124769b46c7061bd6783df1e50f6c"
        "d1fa1abeafe8256180",
        "",
        "533a37f6bbe457251f023c0d88f976ae"
        "2dfb504a843e34d2074fd823d41a591f"
        "2b233f034f628281f2fd7a22ddd47d78"
        "28c59bd0a21bfd3980ff0d2028d4b18a"
        "9df63e006c5d1c2d345b925d8dc00b41"
        "04852db99ac5c7cdda8530a113a0f4db"
        "b61149f05a7363268c71d95808ff2e65"
        "2600",
    ),
    # 1 octet
    (
        generator_ed448,
        "c4eab05d357007c632f3dbb48489924d"
        "552b08fe0c353a0d4a1f00acda2c463a"
        "fbea67c5e8d2877c5e3bc397a659949e"
        "f8021e954e0a12274e",
        "43ba28f430cdff456ae531545f7ecd0a"
        "c834a55d9358c0372bfa0c6c6798c086"
        "6aea01eb00742802b8438ea4cb82169c"
        "235160627b4c3a9480",
        "03",
        "26b8f91727bd62897af15e41eb43c377"
        "efb9c610d48f2335cb0bd0087810f435"
        "2541b143c4b981b7e18f62de8ccdf633"
        "fc1bf037ab7cd779805e0dbcc0aae1cb"
        "cee1afb2e027df36bc04dcecbf154336"
        "c19f0af7e0a6472905e799f1953d2a0f"
        "f3348ab21aa4adafd1d234441cf807c0"
        "3a00",
    ),
    # 11 octets
    (
        generator_ed448,
        "cd23d24f714274e744343237b93290f5"
        "11f6425f98e64459ff203e8985083ffd"
        "f60500553abc0e05cd02184bdb89c4cc"
        "d67e187951267eb328",
        "dcea9e78f35a1bf3499a831b10b86c90"
        "aac01cd84b67a0109b55a36e9328b1e3"
        "65fce161d71ce7131a543ea4cb5f7e9f"
        "1d8b00696447001400",
        "0c3e544074ec63b0265e0c",
        "1f0a8888ce25e8d458a21130879b840a"
        "9089d999aaba039eaf3e3afa090a09d3"
        "89dba82c4ff2ae8ac5cdfb7c55e94d5d"
        "961a29fe0109941e00b8dbdeea6d3b05"
        "1068df7254c0cdc129cbe62db2dc957d"
        "bb47b51fd3f213fb8698f064774250a5"
        "028961c9bf8ffd973fe5d5c206492b14"
        "0e00",
    ),
    # 12 octets
    (
        generator_ed448,
        "258cdd4ada32ed9c9ff54e63756ae582"
        "fb8fab2ac721f2c8e676a72768513d93"
        "9f63dddb55609133f29adf86ec9929dc"
        "cb52c1c5fd2ff7e21b",
        "3ba16da0c6f2cc1f30187740756f5e79"
        "8d6bc5fc015d7c63cc9510ee3fd44adc"
        "24d8e968b6e46e6f94d19b945361726b"
        "d75e149ef09817f580",
        "64a65f3cdedcdd66811e2915",
        "7eeeab7c4e50fb799b418ee5e3197ff6"
        "bf15d43a14c34389b59dd1a7b1b85b4a"
        "e90438aca634bea45e3a2695f1270f07"
        "fdcdf7c62b8efeaf00b45c2c96ba457e"
        "b1a8bf075a3db28e5c24f6b923ed4ad7"
        "47c3c9e03c7079efb87cb110d3a99861"
        "e72003cbae6d6b8b827e4e6c143064ff"
        "3c00",
    ),
    # 13 octets
    (
        generator_ed448,
        "7ef4e84544236752fbb56b8f31a23a10"
        "e42814f5f55ca037cdcc11c64c9a3b29"
        "49c1bb60700314611732a6c2fea98eeb"
        "c0266a11a93970100e",
        "b3da079b0aa493a5772029f0467baebe"
        "e5a8112d9d3a22532361da294f7bb381"
        "5c5dc59e176b4d9f381ca0938e13c6c0"
        "7b174be65dfa578e80",
        "64a65f3cdedcdd66811e2915e7",
        "6a12066f55331b6c22acd5d5bfc5d712"
        "28fbda80ae8dec26bdd306743c5027cb"
        "4890810c162c027468675ecf645a8317"
        "6c0d7323a2ccde2d80efe5a1268e8aca"
        "1d6fbc194d3f77c44986eb4ab4177919"
        "ad8bec33eb47bbb5fc6e28196fd1caf5"
        "6b4e7e0ba5519234d047155ac727a105"
        "3100",
    ),
    # 64 octets
    (
        generator_ed448,
        "d65df341ad13e008567688baedda8e9d"
        "cdc17dc024974ea5b4227b6530e339bf"
        "f21f99e68ca6968f3cca6dfe0fb9f4fa"
        "b4fa135d5542ea3f01",
        "df9705f58edbab802c7f8363cfe5560a"
        "b1c6132c20a9f1dd163483a26f8ac53a"
        "39d6808bf4a1dfbd261b099bb03b3fb5"
        "0906cb28bd8a081f00",
        "bd0f6a3747cd561bdddf4640a332461a"
        "4a30a12a434cd0bf40d766d9c6d458e5"
        "512204a30c17d1f50b5079631f64eb31"
        "12182da3005835461113718d1a5ef944",
        "554bc2480860b49eab8532d2a533b7d5"
        "78ef473eeb58c98bb2d0e1ce488a98b1"
        "8dfde9b9b90775e67f47d4a1c3482058"
        "efc9f40d2ca033a0801b63d45b3b722e"
        "f552bad3b4ccb667da350192b61c508c"
        "f7b6b5adadc2c8d9a446ef003fb05cba"
        "5f30e88e36ec2703b349ca229c267083"
        "3900",
    ),
    # 256 octets
    (
        generator_ed448,
        "2ec5fe3c17045abdb136a5e6a913e32a"
        "b75ae68b53d2fc149b77e504132d3756"
        "9b7e766ba74a19bd6162343a21c8590a"
        "a9cebca9014c636df5",
        "79756f014dcfe2079f5dd9e718be4171"
        "e2ef2486a08f25186f6bff43a9936b9b"
        "fe12402b08ae65798a3d81e22e9ec80e"
        "7690862ef3d4ed3a00",
        "15777532b0bdd0d1389f636c5f6b9ba7"
        "34c90af572877e2d272dd078aa1e567c"
        "fa80e12928bb542330e8409f31745041"
        "07ecd5efac61ae7504dabe2a602ede89"
        "e5cca6257a7c77e27a702b3ae39fc769"
        "fc54f2395ae6a1178cab4738e543072f"
        "c1c177fe71e92e25bf03e4ecb72f47b6"
        "4d0465aaea4c7fad372536c8ba516a60"
        "39c3c2a39f0e4d832be432dfa9a706a6"
        "e5c7e19f397964ca4258002f7c0541b5"
        "90316dbc5622b6b2a6fe7a4abffd9610"
        "5eca76ea7b98816af0748c10df048ce0"
        "12d901015a51f189f3888145c03650aa"
        "23ce894c3bd889e030d565071c59f409"
        "a9981b51878fd6fc110624dcbcde0bf7"
        "a69ccce38fabdf86f3bef6044819de11",
        "c650ddbb0601c19ca11439e1640dd931"
        "f43c518ea5bea70d3dcde5f4191fe53f"
        "00cf966546b72bcc7d58be2b9badef28"
        "743954e3a44a23f880e8d4f1cfce2d7a"
        "61452d26da05896f0a50da66a239a8a1"
        "88b6d825b3305ad77b73fbac0836ecc6"
        "0987fd08527c1a8e80d5823e65cafe2a"
        "3d00",
    ),
    # 1023 octets
    (
        generator_ed448,
        "872d093780f5d3730df7c212664b37b8"
        "a0f24f56810daa8382cd4fa3f77634ec"
        "44dc54f1c2ed9bea86fafb7632d8be19"
        "9ea165f5ad55dd9ce8",
        "a81b2e8a70a5ac94ffdbcc9badfc3feb"
        "0801f258578bb114ad44ece1ec0e799d"
        "a08effb81c5d685c0c56f64eecaef8cd"
        "f11cc38737838cf400",
        "6ddf802e1aae4986935f7f981ba3f035"
        "1d6273c0a0c22c9c0e8339168e675412"
        "a3debfaf435ed651558007db4384b650"
        "fcc07e3b586a27a4f7a00ac8a6fec2cd"
        "86ae4bf1570c41e6a40c931db27b2faa"
        "15a8cedd52cff7362c4e6e23daec0fbc"
        "3a79b6806e316efcc7b68119bf46bc76"
        "a26067a53f296dafdbdc11c77f7777e9"
        "72660cf4b6a9b369a6665f02e0cc9b6e"
        "dfad136b4fabe723d2813db3136cfde9"
        "b6d044322fee2947952e031b73ab5c60"
        "3349b307bdc27bc6cb8b8bbd7bd32321"
        "9b8033a581b59eadebb09b3c4f3d2277"
        "d4f0343624acc817804728b25ab79717"
        "2b4c5c21a22f9c7839d64300232eb66e"
        "53f31c723fa37fe387c7d3e50bdf9813"
        "a30e5bb12cf4cd930c40cfb4e1fc6225"
        "92a49588794494d56d24ea4b40c89fc0"
        "596cc9ebb961c8cb10adde976a5d602b"
        "1c3f85b9b9a001ed3c6a4d3b1437f520"
        "96cd1956d042a597d561a596ecd3d173"
        "5a8d570ea0ec27225a2c4aaff26306d1"
        "526c1af3ca6d9cf5a2c98f47e1c46db9"
        "a33234cfd4d81f2c98538a09ebe76998"
        "d0d8fd25997c7d255c6d66ece6fa56f1"
        "1144950f027795e653008f4bd7ca2dee"
        "85d8e90f3dc315130ce2a00375a318c7"
        "c3d97be2c8ce5b6db41a6254ff264fa6"
        "155baee3b0773c0f497c573f19bb4f42"
        "40281f0b1f4f7be857a4e59d416c06b4"
        "c50fa09e1810ddc6b1467baeac5a3668"
        "d11b6ecaa901440016f389f80acc4db9"
        "77025e7f5924388c7e340a732e554440"
        "e76570f8dd71b7d640b3450d1fd5f041"
        "0a18f9a3494f707c717b79b4bf75c984"
        "00b096b21653b5d217cf3565c9597456"
        "f70703497a078763829bc01bb1cbc8fa"
        "04eadc9a6e3f6699587a9e75c94e5bab"
        "0036e0b2e711392cff0047d0d6b05bd2"
        "a588bc109718954259f1d86678a579a3"
        "120f19cfb2963f177aeb70f2d4844826"
        "262e51b80271272068ef5b3856fa8535"
        "aa2a88b2d41f2a0e2fda7624c2850272"
        "ac4a2f561f8f2f7a318bfd5caf969614"
        "9e4ac824ad3460538fdc25421beec2cc"
        "6818162d06bbed0c40a387192349db67"
        "a118bada6cd5ab0140ee273204f628aa"
        "d1c135f770279a651e24d8c14d75a605"
        "9d76b96a6fd857def5e0b354b27ab937"
        "a5815d16b5fae407ff18222c6d1ed263"
        "be68c95f32d908bd895cd76207ae7264"
        "87567f9a67dad79abec316f683b17f2d"
        "02bf07e0ac8b5bc6162cf94697b3c27c"
        "d1fea49b27f23ba2901871962506520c"
        "392da8b6ad0d99f7013fbc06c2c17a56"
        "9500c8a7696481c1cd33e9b14e40b82e"
        "79a5f5db82571ba97bae3ad3e0479515"
        "bb0e2b0f3bfcd1fd33034efc6245eddd"
        "7ee2086ddae2600d8ca73e214e8c2b0b"
        "db2b047c6a464a562ed77b73d2d841c4"
        "b34973551257713b753632efba348169"
        "abc90a68f42611a40126d7cb21b58695"
        "568186f7e569d2ff0f9e745d0487dd2e"
        "b997cafc5abf9dd102e62ff66cba87",
        "e301345a41a39a4d72fff8df69c98075"
        "a0cc082b802fc9b2b6bc503f926b65bd"
        "df7f4c8f1cb49f6396afc8a70abe6d8a"
        "ef0db478d4c6b2970076c6a0484fe76d"
        "76b3a97625d79f1ce240e7c576750d29"
        "5528286f719b413de9ada3e8eb78ed57"
        "3603ce30d8bb761785dc30dbc320869e"
        "1a00",
    ),
]


@pytest.mark.parametrize(
    "generator,private_key,public_key,message,signature",
    TEST_VECTORS,
)
def test_vectors(generator, private_key, public_key, message, signature):
    private_key = a2b_hex(private_key)
    public_key = a2b_hex(public_key)
    message = a2b_hex(message)
    signature = a2b_hex(signature)

    sig_key = PrivateKey(generator, private_key)
    ver_key = PublicKey(generator, public_key)

    assert sig_key.public_key().public_key() == ver_key.public_key()

    gen_sig = sig_key.sign(message)

    assert gen_sig == signature

    assert ver_key.verify(message, signature)
