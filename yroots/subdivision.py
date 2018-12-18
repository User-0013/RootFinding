"""
Subdivision provides a solve function that finds roots of a set of functions
by approximating the functions with Chebyshev polynomials.
When the approximation is performed on a sufficiently small interval,
the approximation degree is small enough to be solved efficiently.

"""

import numpy as np
from numpy.fft.fftpack import fftn
from yroots.OneDimension import divCheb,divPower,multCheb,multPower,solve
from yroots.Division import division
from yroots.utils import clean_zeros_from_matrix, slice_top, MacaulayError, get_var_list
from yroots.polynomial import MultiCheb, Polynomial
from yroots.intervalChecks import constant_term_check, full_quad_check, quad_check, full_cubic_check,\
            cubic_check, curvature_check, linear_check, quadratic_check1, quadratic_check2, quadratic_check3
from itertools import product
from matplotlib import pyplot as plt
from matplotlib import patches
import itertools
import time

def solve(funcs, a, b, plot = False, plot_intervals = False):
    '''
    Finds the real roots of the given list of functions on a given interval.

    Parameters
    ----------
    funcs : list of vectorized, callable functions
        Functions to find the common roots of.
        More efficient if functions have an 'evaluate_grid' method handle
        function evaluation at an grid of points.
    a : numpy array
        The lower bound on the interval.
    b : numpy array
        The upper bound on the interval.

    If finding roots of a univariate function, `funcs` does not need to be a list,
    and `a` and `b` can be floats instead of arrays.

    returns
    -------
    roots : numpy array
        The common roots of the polynomials. Each row is a root.
    '''
    interval_checks = [constant_term_check, full_quad_check, full_cubic_check]
    subinterval_checks = [linear_check, quadratic_check1, quadratic_check2]
    interval_results = []
    for i in range(len(interval_checks) + len(subinterval_checks) + 2):
        interval_results.append([])

    if not isinstance(funcs,list):
        funcs = [funcs]
        dim = 1
    elif not isinstance(a, np.ndarray) or not isinstance(b, np.ndarray):
        dim = 1
    else:
        dim = len(a)
    if dim == 1:
        #one dimensional case
        zeros = subdivision_solve_1d(funcs[0],a,b)
        if plot:
            x = np.linspace(a,b,1000)
            for f in funcs:
                plt.plot(x,f(x),color='k')
            plt.plot(np.real(zeros),np.zeros(len(zeros)),'o',color = 'none',markeredgecolor='r')
            plt.show()
        return zeros
    else:
        #multidimensional case

        #make a and b the right type
        a = np.float64(a)
        b = np.float64(b)
        #choose an appropriate max degree for the given dimension
        deg_dim = {2:5, 3:4, 4:3}
        if dim > 4:
            deg = 2
        else:
            deg = deg_dim[dim]

        #Output the interval percentages
        zeros = subdivision_solve_nd(funcs,a,b,deg,interval_results,interval_checks,subinterval_checks)

#colors: use alpha = .5, dark green, black, orange roots. Change colors of check info plots
#3D plot with small alpha, matplotlib interactive, animation
#make logo
#make easier to input lower/upper bounds as a list

        #Plot what happened
        if plot and dim == 2:
            plt.figure(dpi=1200)
            fig,ax = plt.subplots(1)
            fig.set_size_inches(10, 10)
            plt.xlim(a[0],b[0])
            plt.xlabel('$x$')
            plt.ylim(a[1],b[1])
            plt.ylabel('$y$')
            plt.title('Zero-Loci and Roots')

            results_numbers = np.array([len(i) for i in interval_results])
            total_intervals = sum(results_numbers)
            checkers = [func.__name__ for func in interval_checks]+[func.__name__ for func in subinterval_checks]+\
                    ["Division"] + ['Base Case']

            #print the contours
            contour_colors = ['#003cff','k'] #royal blue and black
            x = np.linspace(a[0],b[0],100)
            y = np.linspace(a[1],b[1],100)
            X,Y = np.meshgrid(x,y)
            for i in range(dim):
                if isinstance(funcs[i], Polynomial):
                    Z = np.zeros_like(X)
                    for spot,num in np.ndenumerate(X):
                        Z[spot] = funcs[i]([X[spot],Y[spot]])
                    plt.contour(X,Y,Z,levels=[0],colors=contour_colors[i])
                else:
                    plt.contour(X,Y,funcs[i](X,Y),levels=[0],colors=contour_colors[i])

            #Plot the zeros
            plt.plot(np.real(zeros[:,0]), np.real(zeros[:,1]),'o',color='none',markeredgecolor='r',markersize=10)
            colors = ['w','#d3d3d3', '#708090', '#c5af7d', '#897A57', '#D6C7A4','#73e600','#ccff99']

            if plot_intervals:
                print("Total intervals checked was {}".format(total_intervals))
                print("Methods used were {}".format(checkers))
                print("The percent solved by each was {}".format((100*results_numbers / total_intervals).round(2)))
                plt.title('What happened to the intervals')
                #plot interval checks
                for i in range(len(interval_checks)):
                    results = interval_results[i]
                    first = True
                    for data in results:
                        a0,b0 = data
                        if first:
                            first = False
                            rect = patches.Rectangle((a0[0],a0[1]),b0[0]-a0[0],b0[1]-a0[1],linewidth=.05,\
                                                     edgecolor='k',facecolor=colors[i]\
                                                     , label = interval_checks[i].__name__)
                        else:
                            rect = patches.Rectangle((a0[0],a0[1]),b0[0]-a0[0],b0[1]-a0[1],linewidth=.05,\
                                                     edgecolor='k',facecolor=colors[i])
                        ax.add_patch(rect)
                #subinterval checks
                for i in range(len(interval_checks), len(interval_checks) + len(subinterval_checks)):
                    results = interval_results[i]
                    first = True
                    for data in results:
                        a0,b0 = data
                        if first:
                            first = False
                            rect = patches.Rectangle((a0[0],a0[1]),b0[0]-a0[0],b0[1]-a0[1],linewidth=.05,\
                                                     edgecolor='k',facecolor=colors[i]\
                                                     , label = subinterval_checks[i - len(interval_checks)].__name__)
                        else:
                            rect = patches.Rectangle((a0[0],a0[1]),b0[0]-a0[0],b0[1]-a0[1],linewidth=.05,\
                                                     edgecolor='k',facecolor=colors[i])
                        ax.add_patch(rect)

                i = len(interval_checks) +len(subinterval_checks)
                results = interval_results[i]
                first = True
                #plot basecase and division solve
                for data in results:
                    a0,b0 = data
                    if first:
                        first = False
                        rect = patches.Rectangle((a0[0],a0[1]),b0[0]-a0[0],b0[1]-a0[1],linewidth=.05,\
                                                 edgecolor='k',facecolor=colors[i], label = 'Division Solve')
                    else:
                        rect = patches.Rectangle((a0[0],a0[1]),b0[0]-a0[0],b0[1]-a0[1],linewidth=.05,\
                                                 edgecolor='k',facecolor=colors[i])
                    ax.add_patch(rect)

                i = len(interval_checks) +len(subinterval_checks) + 1
                results = interval_results[i]
                first = True
                for data in results:
                    a0,b0 = data
                    if first:
                        first = False
                        rect = patches.Rectangle((a0[0],a0[1]),b0[0]-a0[0],b0[1]-a0[1],linewidth=.05,\
                                                 edgecolor='k',facecolor=colors[i], label = 'Base Case')
                    else:
                        rect = patches.Rectangle((a0[0],a0[1]),b0[0]-a0[0],b0[1]-a0[1],linewidth=.05,\
                                                 edgecolor='k',facecolor=colors[i])
                    ax.add_patch(rect)
                plt.legend()
            plt.show()

        return zeros

def transform(x,a,b):
    """Transforms points from the interval [-1,1] to the interval [a,b].

    Parameters
    ----------
    x : numpy array
        The points to be tranformed.
    a : float or numpy array
        The lower bound on the interval. Float if one-dimensional, numpy array if multi-dimensional
    b : float or numpy array
        The upper bound on the interval. Float if one-dimensional, numpy array if multi-dimensional

    Returns
    -------
    transform : numpy array
        The transformed points.
    """
    return ((b-a)*x+(b+a))/2

def chebyshev_block_copy(values_block):
    """This functions helps avoid double evaluation of functions at
    interpolation points. It takes in a tensor of function evaluation values
    and copies these values to a new tensor appropriately to prepare for
    chebyshev interpolation.

    Parameters
    ----------
    block_values : numpy array
      block of values from function evaluation

    Returns
    -------
    cheb_values : numpy array
      chebyshev interpolation values
    """
    dim = values_block.ndim
    deg = values_block.shape[0] - 1
    values_cheb = np.empty(tuple([2*deg])*dim, dtype=values_block.dtype)

    for block in product([False,True],repeat=dim):
        cheb_idx = [slice(0,deg+1)]*dim
        block_idx = [slice(None)]*dim
        for i,flip_dim in enumerate(block):
            if flip_dim:
                cheb_idx[i] = slice(deg+1,None)
                block_idx[i] = slice(deg-1,0,-1)
        values_cheb[tuple(cheb_idx)] = values_block[tuple(block_idx)]
    return values_cheb

def interval_approximate_1d(f,a,b,deg):
    """Finds the chebyshev approximation of a one-dimensional function on an interval.

    Parameters
    ----------
    f : function from R -> R
        The function to interpolate.
    a : float
        The lower bound on the interval.
    b : float
        The upper bound on the interval.
    deg : int
        The degree of the interpolation.

    Returns
    -------
    coeffs : numpy array
        The coefficient of the chebyshev interpolating polynomial.
    """
    extrema = transform(np.cos((np.pi*np.arange(2*deg))/deg),a,b)
    values = f(extrema)
    coeffs = np.real(np.fft.fft(values/deg))
    coeffs[0]/=2
    coeffs[deg]/=2
    return coeffs[:deg+1]

def interval_approximate_nd(f,a,b,degs,return_bools=False):
    """Finds the chebyshev approximation of an n-dimensional function on an interval.

    Parameters
    ----------
    f : function from R^n -> R
        The function to interpolate.
    a : numpy array
        The lower bound on the interval.
    b : numpy array
        The upper bound on the interval.
    deg : numpy array
        The degree of the interpolation in each dimension.
    return_bools: bool
        whether to return bools which indicate if a funtion changes sign or not

    Returns
    -------
    coeffs : numpy array
        The coefficient of the chebyshev interpolating polynomial.
    change_sign: numpy array
        list of which subintervals change sign
    """
    if len(a)!=len(b):
        raise ValueError("Interval dimensions must be the same!")

    dim = len(a)
    deg = degs[0]

    if hasattr(f,"evaluate_grid"):
        cheb_values = np.cos(np.arange(deg+1)*np.pi/deg)
        xyz = transform(np.column_stack([cheb_values]*dim), a, b)
        values_block = f.evaluate_grid(xyz)
    else:
        cheb_values = np.cos(np.arange(deg+1)*np.pi/deg)
        cheb_grids = np.meshgrid(*([cheb_values]*dim), indexing='ij')

        flatten = lambda x: x.flatten()
        cheb_points = transform(np.column_stack(map(flatten, cheb_grids)), a, b)
        cheb_points = [cheb_points[:,i] for i in range(dim)]
        values_block = f(*cheb_points).reshape(*([deg+1]*dim))

    slices = []
    for i in range(dim):
        slices.append(slice(0,degs[i]+1))

    #figure out on which subintervals the function changes sign
    if return_bools:
        change_sign = np.ones(2**dim, dtype=bool)

        split = 0.027860780181747646 #from RAND below
        split_point = len(np.where(cheb_values>split)[0])

        for k, subinterval in enumerate(product([False,True], repeat=dim)):
            slicer = []*dim
            for i in range(dim):
                if subinterval[i]:
                    slicer.append(slice(split_point,None))
                else:
                    slicer.append(slice(None,split_point))

            if np.all(values_block[tuple(slicer)]>0) or np.all(values_block[tuple(slicer)]<0):
                change_sign[k] = False

    values = chebyshev_block_copy(values_block)
    coeffs = np.real(fftn(values/np.product(degs)))

    for i in range(dim):
        #construct slices for the first and degs[i] entry in each dimension
        idx0 = [slice(None)] * dim
        idx0[i] = 0

        idx_deg = [slice(None)] * dim
        idx_deg[i] = degs[i]

        #halve the coefficients in each slice
        coeffs[tuple(idx0)] /= 2
        coeffs[tuple(idx_deg)] /= 2

    if return_bools:
        return coeffs[tuple(slices)], change_sign
    else:
        return coeffs[tuple(slices)]

def get_subintervals(a,b,dimensions,subinterval_checks,interval_results,polys,change_sign,approx_tol,check_subintervals=False):
    """Gets the subintervals to divide a search interval into.

    Parameters
    ----------
    a : numpy array
        The lower bound on the interval.
    b : numpy array
        The upper bound on the interval.
    dimensions : numpy array
        The dimensions we want to cut in half.

    Returns
    -------
    subintervals : list
        Each element of the list is a tuple containing an a and b, the lower and upper bounds of the interval.
    """
    RAND = 0.5139303900908738
    subintervals = []
    diffs1 = ((b-a)*RAND)[dimensions]
    diffs2 = ((b-a)-(b-a)*RAND)[dimensions]

    for subset in product([False,True], repeat=len(dimensions)):
        subset = np.array(subset)
        aTemp = a.copy()
        bTemp = b.copy()
        aTemp[dimensions] += (~subset)*diffs1
        bTemp[dimensions] -= subset*diffs2
        subintervals.append((aTemp,bTemp))

    if check_subintervals:
        scaled_subintervals = get_subintervals(-np.ones_like(a),np.ones_like(a),dimensions,subinterval_checks=None,\
                                                interval_results=None,polys=None,change_sign=None,approx_tol=approx_tol,check_subintervals=False)
        for check_num, check in enumerate(subinterval_checks):
            for poly in polys:
                mask = check(poly, scaled_subintervals, change_sign, approx_tol)
                new_scaled_subintervals = []
                new_subintervals = []
                for i, result in enumerate(mask):
                    if result:
                        new_scaled_subintervals.append(scaled_subintervals[i])
                        new_subintervals.append(subintervals[i])
                    else:
                        interval_results[check_num-(2+len(subinterval_checks))].append(subintervals[i])
                scaled_subintervals = new_scaled_subintervals
                subintervals = new_subintervals

    return subintervals

def full_cheb_approximate(f,a,b,deg,tol=1.e-8):
    """Gives the full chebyshev approximation and checks if it's good enough.

    Called recursively.

    Parameters
    ----------
    f : function
        The function we approximate.
    a : numpy array
        The lower bound on the interval.
    b : numpy array
        The upper bound on the interval.
    deg : int
        The degree to approximate with.
    tol : float
        How small the high degree terms must be to consider the approximation accurate.

    Returns
    -------
    coeff : numpy array
        The coefficient array of the interpolation. If it can't get a good approximation and needs to subdivide, returns None.
    bools: numpy array
        (2^n, 1) array of bools corresponding to which subintervals the function changes sign in
    """
    dim = len(a)
    degs = np.array([deg]*dim)
    coeff = interval_approximate_nd(f,a,b,degs)
    coeff2, bools = interval_approximate_nd(f,a,b,degs*2,return_bools=True)
    coeff2[slice_top(coeff)] -= coeff
    clean_zeros_from_matrix(coeff2,1.e-16)
    if np.sum(np.abs(coeff2)) > tol:
        return None, None
    else:
        return coeff, bools

def good_zeros_nd(zeros, imag_tol = 1.e-5, real_tol = 1.e-5):
    """Get the real zeros in the -1 to 1 interval in each dimension.

    Parameters
    ----------
    zeros : numpy array
        The zeros to be checked.
    imag_tol : float
        How large the imaginary part can be to still have it be considered real.

    Returns
    -------
    good_zeros : numpy array
        The real zero in [-1,1] of the input zeros.
    """
    good_zeros = zeros[np.all(np.abs(zeros.imag) < imag_tol,axis = 1)]
    good_zeros = good_zeros[np.all(np.abs(good_zeros) <= 1 + real_tol,axis = 1)]
    return good_zeros.real

def subdivision_solve_nd(funcs,a,b,deg,interval_results,interval_checks = [],subinterval_checks=[],approx_tol=1.e-4, cutoff_tol=1.e-5, solve_tol = 1.e-8):
    """Finds the common zeros of the given functions.

    Parameters
    ----------
    funcs : list
        Each element of the list is a callable function.
    a : numpy array
        The lower bound on the interval.
    b : numpy array
        The upper bound on the interval.
    deg : int
        The degree to approximate with in the chebyshev approximation.

    Returns
    -------
    good_zeros : numpy array
        The real zero in [-1,1] of the input zeros.
    """
    cheb_approx_list = []
    try:
        if np.random.rand() > .99: #replace this with a progress bar
            print("Interval - ",a,b)
        dim = len(a)
        for func in funcs:
            coeff, change_sign = full_cheb_approximate(func,a,b,deg,tol=approx_tol)

            #Subdivides if a bad approximation
            if coeff is None:
                intervals = get_subintervals(a,b,np.arange(dim),None,None,None,approx_tol,None)

                return np.vstack([subdivision_solve_nd(funcs,interval[0],interval[1],deg,interval_results\
                                                       ,interval_checks,subinterval_checks,approx_tol=approx_tol)
                                  for interval in intervals])
            else:
                #if the function changes sign on at least one subinterval, skip the checks
                if np.any(change_sign):
                    cheb_approx_list.append(coeff)
                    continue
                #Run checks to try and throw out the interval
                for func_num, func in enumerate(interval_checks):
                    if not func(coeff, approx_tol):
                        interval_results[func_num].append([a,b])
                        return np.zeros([0,dim])
                cheb_approx_list.append(coeff)

        #Make the system stable to solve
        polys, divisor_var = trim_coeffs(cheb_approx_list, approx_tol = approx_tol, tol=cutoff_tol)

        #Check if everything is linear
        if np.all(np.array([poly.degree for poly in polys]) == 1):
            A = np.zeros([dim,dim])
            B = np.zeros(dim)
            for row in range(dim):
                coeff = polys[row].coeff
                spot = tuple([0]*dim)
                B[row] = coeff[spot]
                var_list = get_var_list(dim)
                for col in range(dim):
                    A[row,col] = coeff[var_list[col]]

            zero = np.linalg.solve(A,-B)
            interval_results[-1].append([a,b])
            return transform(zero,a,b)

            if np.all(zero >= a) and np.all(zero <= b):
                return transform(zero)
            else:
                return np.zeros([0,dim])
        if divisor_var < 0:
            #Subdivide but run some checks on the intervals first
            intervals = get_subintervals(a,b,np.arange(dim),subinterval_checks,interval_results\
                                         ,cheb_approx_list,change_sign,approx_tol,check_subintervals=True)
            if len(intervals) == 0:
                return np.zeros([0,dim])
            else:
                return np.vstack([subdivision_solve_nd(funcs,interval[0],interval[1],deg,interval_results\
                                                   ,interval_checks,subinterval_checks,approx_tol=approx_tol)
                              for interval in intervals])

        zeros = np.array(division(polys,divisor_var = divisor_var, tol = solve_tol))
        interval_results[-2].append([a,b])
        if len(zeros) == 0:
            return np.zeros([0,dim])
        return transform(good_zeros_nd(zeros),a,b)

    except np.linalg.LinAlgError as e:
        #Subdivide but run some checks on the intervals first
        intervals = get_subintervals(a,b,np.arange(dim),subinterval_checks,interval_results\
                                     ,cheb_approx_list,change_sign,approx_tol,check_subintervals=True)
        if len(intervals) == 0:
            return np.zeros([0,dim])
        else:
            return np.vstack([subdivision_solve_nd(funcs,interval[0],interval[1],deg,interval_results\
                                               ,interval_checks,subinterval_checks,approx_tol=approx_tol)
                          for interval in intervals])

def trim_coeffs(coeffs, approx_tol, tol):
    """Trim the coefficient matrices so they are stable and choose a direction to divide in.

    Parameters
    ----------
    coeffs : list
        The coefficient matrices of the Chebyshev polynomials we are solving.

    Returns
    -------
    polys : list
        The reduced degree Chebyshev polynomials
    divisor_var : int
        What direction to do the division in to be stable. -1 means we should subdivide.
    """
    dim = coeffs[0].ndim
    error = [0.]*len(coeffs)
    degrees = [np.sum(coeffs[0].shape)-dim]*dim
    first_time = True

    while True:
        changed = False
        for num, coeff in enumerate(coeffs):
            deg = degrees[num]
            if deg <= 1: #This is to not trim past linear
                continue
            mons = mon_combos_limited([0]*dim,deg,coeff.shape)
            slices = [] #becomes the indices of the terms of degree deg
            mons = np.array(mons).T
            if len(mons) == 0:
                continue

            for i in range(dim):
                slices.append(mons[i])

            slice_error = np.sum(np.abs(coeff[tuple(slices)]))
            if error[num] + slice_error < approx_tol:
                error[num] += slice_error
                coeff[tuple(slices)] = 0
                new_slices = [slice(0,deg,None) for i in range(dim)]
                coeff = coeff[tuple(new_slices)]
                changed = True
                degrees[num] -= 1
            coeffs[num] = coeff
        if not changed and not first_time:
            polys = []
            for coeff in coeffs:
                polys.append(MultiCheb(coeff))
            return polys, -1
        d = pick_stable_dim(coeffs, tol=tol)
        if d >= 0:
            polys = []
            for coeff in coeffs:
                polys.append(MultiCheb(coeff))
            return polys, d

        first_time = False

def pick_stable_dim(coeffs, tol = 1.e-5):
    dimension = coeffs[0].ndim
    for dim in range(dimension):
        corner_spots = []
        for i in range(dimension):
            corner_spots.append([])

        for coeff in coeffs:
            spot = [0]*dimension
            for dim2 in range(dimension):
                if dim != dim2:
                    spot[dim2] = coeff.shape[dim2] - 1
                    corner_spots[dim2].append(coeff[tuple(spot)])
                    spot[dim2] = 0
                else:
                    spot[dim2] = 0
                    corner_spots[dim2].append(coeff[tuple(spot)])

        for perm in itertools.permutations(np.arange(dimension)):
            valid = True
            for i,j in enumerate(perm):
                if np.abs(corner_spots[i][j]) < tol:
                    valid = False
                    break
            if valid:
                return dim
    return -1

def mon_combos_limited(mon, remaining_degrees, shape, cur_dim = 0):
    '''Finds all the monomials of a given degree that fits in a given shape and returns them. Works recursively.

    Very similar to mon_combos, but only returns the monomials of the desired degree.

    Parameters
    --------
    mon: list
        A list of zeros, the length of which is the dimension of the desired monomials. Will change
        as the function searches recursively.
    remaining_degrees : int
        Initially the degree of the monomials desired. Will decrease as the function searches recursively.
    shape : tuple
        The limiting shape. The i'th index of the mon can't be bigger than the i'th index of the shape.
    cur_dim : int
        The current position in the list the function is iterating through. Defaults to 0, but increases
        in each step of the recursion.

    Returns
    -----------
    answers : list
        A list of all the monomials.
    '''
    answers = []
    if len(mon) == cur_dim+1: #We are at the end of mon, no more recursion.
        if remaining_degrees < shape[cur_dim]:
            mon[cur_dim] = remaining_degrees
            answers.append(mon.copy())
        return answers
    if remaining_degrees == 0: #Nothing else can be added.
        answers.append(mon.copy())
        return answers
    temp = mon.copy() #Quicker than copying every time inside the loop.
    for i in range(min(shape[cur_dim],remaining_degrees+1)): #Recursively add to mon further down.
        temp[cur_dim] = i
        answers.extend(mon_combos_limited(temp, remaining_degrees-i, shape, cur_dim+1))
    return answers

def good_zeros_1d(zeros, imag_tol = 1.e-10):
    """Get the real zeros in the -1 to 1 interval

    Parameters
    ----------
    zeros : numpy array
        The zeros to be checked.
    imag_tol : float
        How large the imaginary part can be to still have it be considered real.

    Returns
    -------
    good_zeros : numpy array
        The real zero in [-1,1] of the input zeros.
    """
    zeros = zeros[np.where(np.abs(zeros) <= 1)]
    zeros = zeros[np.where(np.abs(zeros.imag) < imag_tol)]
    return zeros

def subdivision_solve_1d(f,a,b,cheb_approx_tol=1.e-3,max_degree=128):
    """Finds the roots of a one-dimensional function using subdivision and chebyshev approximation.

    Parameters
    ----------
    f : function from R^n -> R
        The function to interpolate.
    a : numpy array
        The lower bound on the interval.
    b : numpy array
        The upper bound on the interval.
    deg : int
        The degree of the interpolation.

    Returns
    -------
    coeffs : numpy array
        The coefficient of the chebyshev interpolating polynomial.
    """
    cur_deg = 2
    initial_approx = interval_approximate_1d(f,a,b,deg = cur_deg)
    while cur_deg<=max_degree:
        coeffsN = np.zeros(2*cur_deg+1)
        coeffsN[:cur_deg+1] = initial_approx
        coeffs2N = interval_approximate_1d(f,a,b,deg = 2*cur_deg)
        #Check if the approximation is good enough
        # if np.sum(np.abs(coeffs2N - coeffsN)) < cheb_approx_tol:
        if np.sum(np.abs(coeffs2N[cur_deg+1:])) < cheb_approx_tol:
            coeffs = coeffsN[:cur_deg+1]
            #Division is faster after degree 75
            if cur_deg > 75:
                return transform(good_zeros_1d(divCheb(coeffs)),a,b)
            else:
                return transform(good_zeros_1d(multCheb(np.trim_zeros(coeffs.copy(),trim='b'))),a,b)
        initial_approx = coeffs2N
        cur_deg*=2
    #Subdivide the interval and recursively call the function.
    div_length = (b-a)/2
    return np.hstack([subdivision_solve_1d(f,a,b-div_length,max_degree=max_degree),\
                      subdivision_solve_1d(f,a+div_length,b,max_degree=max_degree)])