"""Example component.

Note that package a and b do not exist so this code does not work,
but conceptually should work if you publish the raptor package repo twice, as package a and b.
"""
# ruff: noqa: T201, INP001

import argparse

from example_package.examples import divide, multiply


def parse_args() -> argparse.Namespace:
    """Function to parse the arguments.

    Returns:
        argparse.Namespace: object with parsed arguments
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--operator", type=str, default="multiply", help="Multiply or divide"
    )
    parser.add_argument("--a", type=float)
    parser.add_argument("--b", type=float)
    return parser.parse_args()


def main() -> None:
    """Main function for this component."""
    args = parse_args()
    if args.operator == "multiply":
        result = multiply(args.a, args.b)
        print(f"{args.a} * {args.b} = {result}")
    else:
        result = divide(args.a, args.b)
        print(f"{args.a} / {args.b} = {result}")


if __name__ == "__main__":
    main()
