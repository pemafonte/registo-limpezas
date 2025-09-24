# Funcionalidades Excel/Pandas reativadas
PANDAS_AVAILABLE = False

try:
    print("DEBUG: Tentando importar pandas...")
    import pandas as pd
    print(f"DEBUG: Pandas importado com sucesso - versão {pd.__version__}")
    print("DEBUG: Tentando importar numpy...")
    import numpy as np
    print(f"DEBUG: Numpy importado com sucesso - versão {np.__version__}")
    PANDAS_AVAILABLE = True
    print("✅ Pandas/Numpy disponível - Funcionalidades Excel ATIVAS")
except ImportError as e:
    print(f"❌ Erro ao importar Pandas/Numpy: {e}")
    print("❌ Pandas/Numpy não disponível - Funcionalidades Excel desabilitadas")
    pd = None
    np = None
except Exception as e:
    print(f"❌ Erro inesperado ao importar Pandas/Numpy: {e}")
    print("❌ Pandas/Numpy não disponível - Funcionalidades Excel desabilitadas")
    pd = None
    np = None
    PANDAS_AVAILABLE = False