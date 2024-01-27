from abc import abstractmethod
from functools import reduce
from itertools import chain

from opt_einsum import contract


class BaseFactor(object):
    """
    Base class for Factors. Any Factor implementation should inherit this class.
    """

    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def is_valid_cpd(self):
        pass


def factor_product(*args):
    """
    Returns factor product over `args`.

    Parameters
    ----------
    args: `BaseFactor` instances.
        factors to be multiplied

    Returns
    -------
    BaseFactor: `BaseFactor` representing factor product over all the `BaseFactor` instances in args.

    Examples
    --------
    >>> from pgmpy.factors.discrete import DiscreteFactor
    >>> from pgmpy.factors import factor_product
    >>> phi1 = DiscreteFactor(['x1', 'x2', 'x3'], [2, 3, 2], range(12))
    >>> phi2 = DiscreteFactor(['x3', 'x4', 'x1'], [2, 2, 2], range(8))
    >>> phi = factor_product(phi1, phi2)
    >>> phi.variables
    ['x1', 'x2', 'x3', 'x4']
    >>> phi.cardinality
    array([2, 3, 2, 2])
    >>> phi.values
    array([[[[ 0,  0],
             [ 4,  6]],

            [[ 0,  4],
             [12, 18]],

            [[ 0,  8],
             [20, 30]]],


           [[[ 6, 18],
             [35, 49]],

            [[ 8, 24],
             [45, 63]],

            [[10, 30],
             [55, 77]]]])
    """
    if not all(isinstance(phi, BaseFactor) for phi in args):
        raise TypeError("Arguments must be factors")
    # Check if all of the arguments are of the same type
    elif len(set(map(type, args))) != 1:
        raise NotImplementedError(
            "All the args are expected to be instances of the same factor class."
        )

    if len(args) == 1:
        return args[0].copy()
    else:
        return reduce(lambda phi1, phi2: phi1 * phi2, args)


def factor_sum_product(output_vars, factors):
    """
    For a given set of factors: `args` returns the result of $ \sum_{var \not \in output_vars} \prod \textit{args} $.

    Parameters
    ----------
    output_vars: list, iterable
        List of variable names on which the output factor is to be defined. Variable which are present in any of the factors
        but not in output_vars will be marginalized out.

    factors: list, iterable
        List of DiscreteFactor objects on which to perform the sum product operation.

    Returns
    -------
    pgmpy.factor.discrete.DiscreteFactor: A DiscreteFactor object on `output_vars`.

    Examples
    --------
    >>> from pgmpy.factors import factor_sum_product
    >>> from pgmpy.utils import get_example_model
    >>> factors = [cpd.to_factor() for cpd in model.cpds]
    >>> factor_sum_product(output_vars=['HISTORY'], factors=factors)
    <DiscreteFactor representing phi(HISTORY:2) at 0x7f240556b970>
    """
    state_names = {}
    for phi in factors:
        state_names.update(phi.state_names)

    einsum_expr = []
    for phi in factors:
        einsum_expr.append(phi.values)
        einsum_expr.append(phi.variables)
    values = contract(*einsum_expr, output_vars, optimize="greedy")

    from pgmpy.factors.discrete import DiscreteFactor

    return DiscreteFactor(
        variables=output_vars,
        cardinality=values.shape,
        values=values,
        state_names={var: state_names[var] for var in output_vars},
    )


def factor_log_sum(*args):
    if not all(isinstance(phi, BaseFactor) for phi in args):
        raise TypeError("Arguments must be log factors")
    # Check if all of the arguments are of the same type
    elif len(set(map(type, args))) != 1:
        raise NotImplementedError(
            "All the args are expected to be instances of the same factor class."
        )

    log_args = [args.log(inplace=False) for args in args]

    if len(log_args) == 1:
        return log_args[0].copy()
    else:
        return reduce(lambda phi1, phi2: phi1 + phi2, log_args)


def factor_divide(phi1, phi2):
    """
    Returns `DiscreteFactor` representing `phi1 / phi2`.

    Parameters
    ----------
    phi1: Factor
        The Dividend.

    phi2: Factor
        The Divisor.

    Returns
    -------
    DiscreteFactor: `DiscreteFactor` representing factor division `phi1 / phi2`.

    Examples
    --------
    >>> from pgmpy.factors.discrete import DiscreteFactor
    >>> from pgmpy.factors import factor_product
    >>> phi1 = DiscreteFactor(['x1', 'x2', 'x3'], [2, 3, 2], range(12))
    >>> phi2 = DiscreteFactor(['x3', 'x1'], [2, 2], range(1, 5))
    >>> phi = factor_divide(phi1, phi2)
    >>> phi.variables
    ['x1', 'x2', 'x3']
    >>> phi.cardinality
    array([2, 3, 2])
    >>> phi.values
    array([[[ 0.        ,  0.33333333],
            [ 2.        ,  1.        ],
            [ 4.        ,  1.66666667]],

           [[ 3.        ,  1.75      ],
            [ 4.        ,  2.25      ],
            [ 5.        ,  2.75      ]]])
    """
    if not isinstance(phi1, BaseFactor) or not isinstance(phi2, BaseFactor):
        raise TypeError("phi1 and phi2 should be factors instances")

    # Check if all of the arguments are of the same type
    elif type(phi1) != type(phi2):
        raise NotImplementedError(
            "All the args are expected to be instances of the same factor class."
        )

    return phi1.divide(phi2, inplace=False)
