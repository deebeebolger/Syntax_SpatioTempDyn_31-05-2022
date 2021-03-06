import mne
import numpy as np
from datetime import datetime
from glob import glob
from os.path import basename, join, splitext
from xml.etree.ElementTree import parse

def _parse_xml(xml_file):
    """Parse XML file."""
    xml = parse(xml_file)
    root = xml.getroot()
    return _xml2list(root)

def _xml2list(root):
    """Parse XML item."""
    output = []
    for element in root:

        if len(element) > 0:
            if element[0].tag != element[-1].tag:
                output.append(_xml2dict(element))
            else:
                output.append(_xml2list(element))

        elif element.text:
            text = element.text.strip()
            if text:
                tag = _ns(element.tag)
                output.append({tag: text})
    return output

def _ns(s):
    """Remove namespace, but only if there is a namespace to begin with."""
    if '}' in s:
        return '}'.join(s.split('}')[1:])
    else:
        return s


def _xml2dict(root):
    """Use functions instead of Class.

    remove namespace based on
    http://stackoverflow.com/questions/2148119
    """
    output = {}
    if root.items():
        output.update(dict(root.items()))

    for element in root:
        if len(element) > 0:
            if len(element) == 1 or element[0].tag != element[1].tag:
                one_dict = _xml2dict(element)
            else:
                one_dict = {_ns(element[0].tag): _xml2list(element)}

            if element.items():
                one_dict.update(dict(element.items()))
            output.update({_ns(element.tag): one_dict})

        elif element.items():
            output.update({_ns(element.tag): dict(element.items())})

        else:
            output.update({_ns(element.tag): element.text})
    return output

def _ns2py_time(nstime):
    """Parse times."""
    nsdate = nstime[0:10]
    nstime0 = nstime[11:26]
    nstime00 = nsdate + " " + nstime0
    pytime = datetime.strptime(nstime00, '%Y-%m-%d %H:%M:%S.%f')
    return pytime

def _combine_triggers(data, remapping=None):
    """Combine binary triggers."""
    new_trigger = np.zeros(data.shape[1])
    if data.astype(bool).sum(axis=0).max() > 1:  # ensure no overlaps
        logger.info('    Found multiple events at the same time '
                    'sample. Cannot create trigger channel.')
        return
    if remapping is None:
        remapping = np.arange(data) + 1
    for d, event_id in zip(data, remapping):
        idx = d.nonzero()
        if np.any(idx):
            new_trigger[idx] += event_id
    return new_trigger

"""****************************** LOAD IN RAW EGI DATA################################"""
fpath = '/Users/bolger/Documents/work/Projects/SpatioTempDyn_Syntax/Data/'
datacurr = '120_20220520_052757.mff'
filename = fpath + datacurr

RawIn = mne.io.read_raw_egi(filename, channel_naming='E%d', verbose=None)   # Load in raw EGI data in *.mff format
sfreq = RawIn.info['sfreq']   # get the sampling frequency

"""Extract the events.

Parameters
----------
filename : str
    File path.
sfreq : float
    The sampling frequency
"""
orig = {}
for xml_file in glob(join(filename, '*.xml')):     # Extracting the xml files composing the current *.mff file.
    xml_type = splitext(basename(xml_file))[0]
    orig[xml_type] = _parse_xml(xml_file)
xml_files = orig.keys()
xml_events = [x for x in xml_files if x[:7] == 'Events_']
for item in orig['info']:
    if 'recordTime' in item:
        start_time = _ns2py_time(item['recordTime'])
        break
markers = []
code = []
for xml in xml_events:
    for event in orig[xml][2:]:
        event_start = _ns2py_time(event['beginTime'])
        start = (event_start - start_time).total_seconds()
        if event['code'] not in code:
            code.append(event['code'])
        marker = {'name': event['code'],
                  'start': start,
                  'start_sample': int(np.fix(start * sfreq)),
                  'end': start + float(event['duration']) / 1e9,
                  'chan': None,
                  }
        markers.append(marker)  # Contains information regarding all event markers (in dict format).
events_tims = dict()
for ev in code:
    trig_samp = list(c['start_sample'] for n,
                     c in enumerate(markers) if c['name'] == ev)
    events_tims.update({ev: trig_samp})    # Defines the onset times of each event in dict format.



