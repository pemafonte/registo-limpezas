# Versão simplificada para deploy - funcionalidades Excel/Pandas desabilitadas temporariamente
PANDAS_AVAILABLE = False

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    print("Pandas/Numpy não disponível - funcionalidades de export Excel desabilitadas")
    pd = None
    np = None