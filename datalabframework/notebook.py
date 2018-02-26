import os
import sys
import json
import datetime

import nbformat

import json
import os.path
import re
import ipykernel
import requests

try:  # Python 3
    from urllib.parse import urljoin
except ImportError:  # Python 2
    from urlparse import urljoin

try:  # Python 3
    from notebook.notebookapp import list_running_servers
except ImportError:  # Python 2
    import warnings
    from IPython.utils.shimmodule import ShimWarning
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=ShimWarning)
        from IPython.html.notebookapp import list_running_servers
            
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert.preprocessors import ClearOutputPreprocessor
from nbconvert.preprocessors.execute import CellExecutionError

from .project import rootpath

def lrchop(s, b='', e='.ipynb'):
    if s.startswith(b) and len(b)>0:
        s = s[len(b):]
    if s.endswith(e) and len(e)>0:
        s = s[:-len(e)]
    return s

def get_notebook_filename():
    """
    Return the full path of the jupyter notebook.
    """
    kernel_id = re.search('kernel-(.*).json',
                          ipykernel.connect.get_connection_file()).group(1)
    servers = list_running_servers()
    for ss in servers:
        response = requests.get(urljoin(ss['url'], 'api/sessions'),
                                params={'token': ss.get('token', '')})
        for nn in json.loads(response.text):
            if nn['kernel']['id'] == kernel_id:
                relative_path = nn['notebook']['path']
                return os.path.join(ss['notebook_dir'], relative_path)

def filename(s=None, ext='.ipynb'):
    if not s:
        s = get_notebook_filename()
        
    s = lrchop(s,rootpath(), ext).lstrip('/')
    (path, name) = os.path.split(s)
    return (path, name)
            
def list_all(path=None, removelist=[]):
    
    if not path:
        path  = rootpath()
    
    if not path:
        path  = '.'

    lst = list()
    for root, dirs, files in os.walk(path):
        
        # don't visit .ipynb_checkpoints directories
        if '.ipynb_checkpoints' in dirs:
            dirs.remove('.ipynb_checkpoints')  
        
        for file in files:
            if file.endswith("nbconvert.ipynb"): 
                continue
            
            if file.endswith(".ipynb"):
                basedir = root[len(path):]
                filename = os.path.join(basedir, file).lstrip('/')
                if not any([filename.startswith(x) for x in removelist]):
                    lst.append(filename)
    return lst

def statistics(filename):
    data = {}
    with open(filename) as f:        
        data = json.load(f)

    stats = {'cells': len(data['cells'])}

    h = dict()
    for c in data['cells']:
        count = h.get(c['cell_type'], 0)
        h[c['cell_type']] = count + 1
    stats.update(h)

    error = {'ename': None, 'evalue': None} 
    for c in data['cells']:
        if c['cell_type']=='code':
            for o in c['outputs']:
                if o['output_type'] == 'error':
                    error = {'ename': o['ename'], 'evalue': o['evalue']}
                    break
    stats.update(error)

    count =0 
    for c in data['cells']:
        if c['cell_type']=='code' and c['execution_count']:
            count +=1
    stats.update({'executed': count})
    
    return stats

def clear(notebook_filename, nbconvert_filename):
    with open(notebook_filename, 'r') as fh:
        nb = nbformat.read(fh, 4)
        
    # check outputs of all the cells
    preprocessor = ClearOutputPreprocessor()
    clear_nb = preprocessor.preprocess(nb, {})[0]
 
    # clear metadata
    clear_nb.metadata = {}
 
    # write the notebook back to disk
    with open(nbconvert_filename, 'w') as fh:
        nbformat.write(clear_nb, fh, 4)

def execute(notebook_filename, path=None, build_dirname='./build', nbconvert_filename_ext='nbconvert.ipynb'):
    if not path:
        path  = rootpath()
    
    if not path:
        path  = '.'


    notebook_filename = '{}/{}'.format(path,notebook_filename)
        
    build_relpath = '{}/{}'.format(build_dirname, os.path.dirname(notebook_filename).lstrip('/'))
    os.makedirs(build_relpath, exist_ok=True)
    
    basename = os.path.basename(notebook_filename)
    parts = basename.split('.')
    
    nbconvert_filename = '.'.join(parts[0:-1] + [nbconvert_filename_ext])
    nbconvert_fullname = '{}/{}'.format(build_relpath,nbconvert_filename)

    walltime= datetime.datetime.now()
    success = 1
    
    # clear the notebook
    clear(notebook_filename, nbconvert_fullname)
    
    #run on the cleared output notebook
    with open(nbconvert_fullname) as f:
        nb = nbformat.read(f, as_version=4)
        try:
            ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
            ep.preprocess(nb, {'metadata': {'path': os.path.dirname(notebook_filename)}})
        except CellExecutionError as e:
            sys.stdout.write('\rError executing notebook "{}".'.format(nbconvert_fullname))
            success = 0
        finally:
            with open(nbconvert_fullname, mode='wt') as f:
                nbformat.write(nb, f)
    walltime = datetime.datetime.now() - walltime
    
    res = {'filename':notebook_filename, 'duration':walltime.total_seconds(), 'success':success}
    stats = statistics(nbconvert_fullname)
    res.update(stats)
    
    return [res]