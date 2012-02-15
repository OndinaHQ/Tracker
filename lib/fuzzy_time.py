#    Copyright (C) 2012  Stefano Palazzo <stefano.palazzo@gmail.com>
#    Copyright (C) 2012  Ondina, LLC. <http://ondina.co>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

NAMES = ((("seconds", "second"), 60),
         (("minutes", "minute"), 60),
         (("hours", "hour"), 24),
         (("days", "day"), 7),
         (("weeks", "week"), 4),
         (("months", "month"), 12),
         (("years", "year"), 1))

def fuzzy_span(u):
    ''' this converts 139 into "two minutes" '''
    u = round(u)
    for n, i in NAMES:
        if u < i:
            break
        else:
            u /= i
    return "%.0f %s" % (round(u), n[1] if round(u) == 1 else n[0])


def fuzzy_delta(now, then):
    ''' this converts 10, 30 into "in 20 seconds" '''
    now, then = int(round(now)), int(round(then))
    if then > now:
        return "in %s" % fuzzy_span(then - now)
    if then < now:
        return "%s ago" % fuzzy_span(now - then)
    if then == now:
        return "just now"
