# Funcionalidades Excel/Pandas reativadas
PANDAS_AVAILABLE = False

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
    print("✅ Pandas/Numpy disponível - Funcionalidades Excel ATIVAS")
except ImportError:
    print("❌ Pandas/Numpy não disponível - Funcionalidades Excel desabilitadas")
    pd = None
    np = None