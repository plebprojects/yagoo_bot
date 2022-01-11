"""
This file is a part of Yagoo Bot <https://yagoo.pleb.moe/>
Copyright (C) 2020-present  ProgrammingPleb

Yagoo Bot is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Yagoo Bot is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Yagoo Bot.  If not, see <http://www.gnu.org/licenses/>.
"""

class ButtonReserved(Exception):
    """
    Exception used for when a button ID which is reserved is attempted to be used.
    
    Arguments
    ---
    keyword: The button ID that is used.
    """
    def __init__(self, keyword):
        super().__init__(f"\"{keyword}\" is a reserved button ID!")

class ButtonNotFound(Exception):
    """
    Exception used for when a button ID which is reserved is attempted to be used.
    
    Arguments
    ---
    keyword: The button ID that is used.
    """
    def __init__(self, keyword):
        super().__init__(f"\"{keyword}\" is not a valid button ID!")
