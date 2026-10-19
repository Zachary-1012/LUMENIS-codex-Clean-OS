# Main-compatible numerical windows

The original main route passes JSON data.get('days_window',21) through int() and data.get('parallel_hours',36) through float(). Query parameters were not used for these windows. The scoped 2248 route introduced days_window type=int and1..365 without an identified owner rule supporting that upper bound. This stage removes that accidental loss instead of documenting it as accepted behavior.

Final implementation preserves those conversions for ordinary finite JSON numbers and numeric strings, including whitespace/signs, float-to-int truncation of day values, >365-day windows, zero and negative windows. Bool, null, invalid numbers and nonfinite data fail closed. These validation failures do not relax permission or source/current pins. The raw supplied payload remains bound to the exact preview resource; normalization does not equate different user confirmations.

Regression cases include800 days as int and string,36.5 as a string,0/-1 windows and3.9-day float conversion. HTTP exercises a string800-day window. This is numerical compatibility, not a grant to query a broader actor/domain scope.
