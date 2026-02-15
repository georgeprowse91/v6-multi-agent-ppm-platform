from sqlalchemy import select, text

def delete(*args, **kwargs):
    return ("delete", args)

def insert(*args, **kwargs):
    return ("insert", args)
