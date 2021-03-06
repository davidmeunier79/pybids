from bids.grabbids import BIDSLayout
import pytest
from os.path import join, dirname, abspath
from bids.tests import get_test_data_path
from bids.variables import DenseRunVariable, merge_collections


@pytest.fixture(scope="module")
def run_coll():
    path = join(get_test_data_path(), 'ds005')
    layout = BIDSLayout(path, exclude='derivatives/')
    return layout.get_collections('run', types=['events'], merge=True,
                                  scan_length=480)


@pytest.fixture(scope="module")
def run_coll_list():
    path = join(get_test_data_path(), 'ds005')
    layout = BIDSLayout(path, exclude='derivatives/')
    return layout.get_collections('run', types=['events'], merge=False,
                                  scan_length=480)


def test_run_variable_collection_init(run_coll):
    assert isinstance(run_coll.variables, dict)
    assert run_coll.sampling_rate == 10


def test_resample_run_variable_collection(run_coll):
    run_coll = run_coll.clone()
    resampled = run_coll.resample()
    assert not resampled  # Empty because all variables are sparse

    resampled = run_coll.resample(force_dense=True)
    assert len(resampled) == 7
    assert all([isinstance(v, DenseRunVariable) for v in resampled.values()])
    assert len(set([v.sampling_rate for v in resampled.values()])) == 1
    targ_len = 480 * 16 * 3 * 10
    assert all([len(v.values) == targ_len for v in resampled.values()])

    sr = 20
    resampled = run_coll.resample(sr, force_dense=True)
    targ_len = 480 * 16 * 3 * sr
    assert all([len(v.values) == targ_len for v in resampled.values()])

    run_coll.resample(sr, force_dense=True, in_place=True)
    assert len(run_coll.variables) == 8
    vars_ = run_coll.variables.values()
    vars_ = [v for v in vars_ if v.name != 'trial_type']
    assert all([len(v.values) == targ_len for v in vars_])
    assert all([v.sampling_rate == sr for v in vars_])
    assert all([isinstance(v, DenseRunVariable) for v in vars_])


def test_run_variable_collection_to_df(run_coll):
    run_coll = run_coll.clone()

    # All variables sparse, wide format
    df = run_coll.to_df()
    assert df.shape == (4096, 13)
    wide_cols = {'onset', 'duration', 'subject', 'run', 'task',
                 'PTval', 'RT', 'gain', 'loss', 'parametric gain', 'respcat',
                 'respnum', 'trial_type'}
    assert set(df.columns) == wide_cols

    # All variables sparse, wide format
    df = run_coll.to_df(format='long')
    assert df.shape == (32768, 7)
    long_cols = {'amplitude', 'duration', 'onset', 'condition', 'run',
                 'task', 'subject'}
    assert set(df.columns) == long_cols

    # All variables dense, wide format
    df = run_coll.to_df(sparse=False)
    assert df.shape == (230400, 14)
    # The inclusion of 'modality' and 'type' here is a minor bug that should
    # be fixed at some point. There is no reason why to_df() should return
    # more columns for a DenseRunVariable than a SparseRunVariable, but this
    # is happening because these columns are not included in the original
    # SparseRunVariable data, and are being rebuilt from the entity list in
    # the DenseRunVariable init.
    wide_cols |= {'modality', 'type'}
    assert set(df.columns) == wide_cols - {'trial_type'}

    # All variables dense, wide format
    df = run_coll.to_df(sparse=False, format='long')
    assert df.shape == (1612800, 9)
    long_cols |= {'modality', 'type'}
    assert set(df.columns) == long_cols


def test_merge_collections(run_coll, run_coll_list):
    df1 = run_coll.to_df().sort_values(['subject', 'run', 'onset'])
    rcl = [c.clone() for c in run_coll_list]
    coll = merge_collections(rcl)
    df2 = coll.to_df().sort_values(['subject', 'run', 'onset'])
    assert df1.equals(df2)


def test_get_collection_entities(run_coll_list):
    coll = run_coll_list[0]
    ents = coll.entities
    assert {'run', 'task', 'subject'} == set(ents.keys())

    merged = merge_collections(run_coll_list[:3])
    ents = merged.entities
    assert {'task', 'subject'} == set(ents.keys())
    assert ents['subject'] == '01'

    merged = merge_collections(run_coll_list[3:6])
    ents = merged.entities
    assert {'task', 'subject'} == set(ents.keys())
    assert ents['subject'] == '02'
