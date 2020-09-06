### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/pupil_config.py

Last updated:  2020-09-06

Configuration for pupil-data handling.
======================================
"""

# Localized field names. This also determines the fields for the PUPIL
# table.
# The localized names may be necessary for importing data.
#TODO: Mark the fields which are used in the program. The others may not
# be needed in particular schools/regions.
PUPIL_FIELDS = {
    'PID'       : 'ID',
    'CLASS'     : 'Klasse',
    'PSORT'     : 'Sortiername',    # ! generated on record entry
    'FIRSTNAME' : 'Rufname',
    'LASTNAME'  : 'Name',
    'STREAM'    : 'Maßstab',        # probably not in imported data
    'FIRSTNAMES': 'Vornamen',
    'DOB_D'     : 'Geburtsdatum',
    'POB'       : 'Geburtsort',
    'SEX'       : 'Geschlecht',
    'HOME'      : 'Ort',
    'ENTRY_D'   : 'Eintrittsdatum',
    'EXIT_D'    : 'Schulaustritt',
    'QUALI_D'   : 'Eintritt-SekII'  # not in imported data
}   # Index : PID
    # Index : (CLASS, PSORT)

