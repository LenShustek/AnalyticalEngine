A scaffold for timing simulations of the proposed small Babbage Analytical Engine
---------------------------------------------------------------------------------

This simulator is designed to estimate the running time of certain operations,
notably multiplication and division, under various architectural assumptions
such as whether a precomputed table of multiplicands or divisors is implemented.

It runs tests with many thousands randomly-generated operands which ar
constrained in various ways.

It then uses the wonderful Python "matplotlib" library to graph the results. 

For our conclusions, see the main proposal paper.
