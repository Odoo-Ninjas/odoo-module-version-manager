import os
import pytest
from unittest.mock import MagicMock

from odoo_version_manager.odoo_version_manager import (
    _get_source_branch,
    _get_mappings,
    _get_github_branches_url,
    _check_no_main_branch,
)


@pytest.fixture(autouse=True)
def main_version_16(monkeypatch):
    monkeypatch.setenv("MAIN_VERSION", "16.0")


# ---------------------------------------------------------------------------
# _get_source_branch
# ---------------------------------------------------------------------------

class TestGetSourceBranch:
    def test_root_returns_none(self):
        assert _get_source_branch("16.0") is None

    def test_below_returns_next_up(self):
        assert _get_source_branch("15.0") == 16.0

    def test_far_below_returns_next_up(self):
        assert _get_source_branch("11.0") == 12.0

    def test_above_returns_next_down(self):
        assert _get_source_branch("17.0") == 16.0

    def test_far_above_returns_next_down(self):
        assert _get_source_branch("19.0") == 18.0


# ---------------------------------------------------------------------------
# _get_mappings
# ---------------------------------------------------------------------------

class TestGetMappings:
    def test_below_maps_to_lower_neighbor(self):
        assert list(_get_mappings("15.0")) == [(14.0, 15.0)]

    def test_above_maps_to_higher_neighbor(self):
        assert list(_get_mappings("17.0")) == [(18.0, 17.0)]

    def test_root_maps_both_neighbors(self):
        mappings = list(_get_mappings("16.0"))
        assert (15.0, 16.0) in mappings
        assert (17.0, 16.0) in mappings
        assert len(mappings) == 2

    def test_root_at_min_version_maps_only_upper(self, monkeypatch):
        monkeypatch.setenv("MAIN_VERSION", "11.0")
        mappings = list(_get_mappings("11.0"))
        assert mappings == [(12.0, 11.0)]

    def test_root_at_max_version_maps_only_lower(self, monkeypatch):
        monkeypatch.setenv("MAIN_VERSION", "19.0")
        mappings = list(_get_mappings("19.0"))
        assert mappings == [(18.0, 19.0)]


# ---------------------------------------------------------------------------
# _get_github_branches_url
# ---------------------------------------------------------------------------

class TestGetGithubBranchesUrl:
    def _repo(self, url):
        repo = MagicMock()
        repo.X.return_value = url + "\n"
        return repo

    def test_ssh_url(self):
        url = _get_github_branches_url(self._repo("git@github.com:myorg/myrepo.git"))
        assert url == "https://github.com/myorg/myrepo/branches"

    def test_https_url_with_git_suffix(self):
        url = _get_github_branches_url(self._repo("https://github.com/myorg/myrepo.git"))
        assert url == "https://github.com/myorg/myrepo/branches"

    def test_https_url_without_git_suffix(self):
        url = _get_github_branches_url(self._repo("https://github.com/myorg/myrepo"))
        assert url == "https://github.com/myorg/myrepo/branches"

    def test_non_github_returns_none(self):
        url = _get_github_branches_url(self._repo("https://gitlab.com/myorg/myrepo.git"))
        assert url is None

    def test_exception_returns_none(self):
        repo = MagicMock()
        repo.X.side_effect = Exception("git error")
        assert _get_github_branches_url(repo) is None


# ---------------------------------------------------------------------------
# _check_no_main_branch
# ---------------------------------------------------------------------------

class TestCheckNoMainBranch:
    def test_no_main_branch_passes(self):
        repo = MagicMock()
        repo.get_all_branches.return_value = ["16.0", "17.0", "15.0"]
        _check_no_main_branch(repo)  # must not raise or exit

    def test_main_exists_without_drift_exits(self):
        repo = MagicMock()
        repo.get_all_branches.return_value = ["16.0", "main"]
        repo.X.return_value = ""  # no commits = no drift

        with pytest.raises(SystemExit) as exc:
            _check_no_main_branch(repo)
        assert exc.value.code == -1

    def test_main_exists_with_drift_exits(self):
        repo = MagicMock()
        repo.get_all_branches.return_value = ["16.0", "main"]

        def x_effect(*args, **kwargs):
            cmd = " ".join(str(a) for a in args)
            if "get-url" in cmd:
                return "https://github.com/org/repo.git\n"
            if "..main" in cmd:
                return "abc1234 commit in main only\n"
            if "main.." in cmd:
                return "xyz9999 commit in version only\n"
            return ""

        repo.X.side_effect = x_effect

        with pytest.raises(SystemExit) as exc:
            _check_no_main_branch(repo)
        assert exc.value.code == -1

    def test_main_exists_shows_github_link(self, capsys):
        repo = MagicMock()
        repo.get_all_branches.return_value = ["16.0", "main"]

        def x_effect(*args, **kwargs):
            cmd = " ".join(str(a) for a in args)
            if "get-url" in cmd:
                return "git@github.com:myorg/myrepo.git\n"
            return ""

        repo.X.side_effect = x_effect

        with pytest.raises(SystemExit):
            _check_no_main_branch(repo)

        captured = capsys.readouterr()
        assert "https://github.com/myorg/myrepo/branches" in captured.out
