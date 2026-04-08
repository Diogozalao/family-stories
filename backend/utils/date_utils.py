MESES_PT = {
    "January": "janeiro", "February": "fevereiro", "March": "março",
    "April": "abril", "May": "maio", "June": "junho",
    "July": "julho", "August": "agosto", "September": "setembro",
    "October": "outubro", "November": "novembro", "December": "dezembro"
}

def data_para_portugues(data_str: str) -> str:
    for en, pt in MESES_PT.items():
        data_str = data_str.replace(en, pt)
    return data_str
