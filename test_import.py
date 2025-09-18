try:
    import main
    print('Main module imported successfully')
except Exception as e:
    print(f'Error importing main: {e}')
    import traceback
    traceback.print_exc()