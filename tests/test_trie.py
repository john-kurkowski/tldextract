"""Trie tests."""

from itertools import permutations

from tldextract.tldextract import Trie


def test_nested_dict() -> None:
    """Test Trie class, built from a list of dot-delimited strings."""
    suffixes = ["a", "d.a", "b.a", "c.b.a", "c", "b.c", "f.d"]
    for suffixes_sequence in permutations(suffixes):
        trie = Trie()
        for suffix in suffixes_sequence:
            trie.add_suffix(suffix)
        # check each nested value
        # Top level c
        assert "c" in trie.matches
        top_c = trie.matches["c"]
        assert len(top_c.matches) == 1
        assert "b" in top_c.matches
        assert top_c.end
        # Top level a
        assert "a" in trie.matches
        top_a = trie.matches["a"]
        assert len(top_a.matches) == 2
        #  a -> d
        assert "d" in top_a.matches
        a_to_d = top_a.matches["d"]
        assert not a_to_d.matches
        #  a -> b
        assert "b" in top_a.matches
        a_to_b = top_a.matches["b"]
        assert a_to_b.end
        assert len(a_to_b.matches) == 1
        #  a -> b -> c
        assert "c" in a_to_b.matches
        a_to_b_to_c = a_to_b.matches["c"]
        assert not a_to_b_to_c.matches
        assert top_a.end
        #  d -> f
        assert "d" in trie.matches
        top_d = trie.matches["d"]
        assert not top_d.end
        assert "f" in top_d.matches
        d_to_f = top_d.matches["f"]
        assert d_to_f.end
        assert not d_to_f.matches
