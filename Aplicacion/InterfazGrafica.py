from cliente import Cliente # cliente OPCUA
import threading
import numpy as np
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import json
import datetime
from collections import deque
import plotly
from dash.dependencies import Output, Input, State
import time
import os
import pandas as pd
from PID import G2_PID


frecMax = 1 # En Hz
Nmuestras = 100  # Valor por defecto para el tamaño del vector memoria

directory = 'HistorialAplicacion'
if not os.path.exists(directory):
        os.makedirs(directory)

eventoColor = 0
eventoTexto = 0
# Función que se suscribe
def funcion_handler(node, val):
    key = node.get_parent().get_display_name().Text
    variables_manipuladas[key] = val # Se cambia globalmente el valor de las variables manipuladas cada vez que estas cambian
    print('key: {} | val: {}'.format(key, val))



class SubHandler(object): # Clase debe estar en el script porque el thread que comienza debe mover variables globales
    def datachange_notification(self, node, val, data):
        thread_handler = threading.Thread(target=funcion_handler, args=(node, val))  # Se realiza la descarga por un thread
        thread_handler.start()

    def event_notification(self, event):
        global eventoColor, eventoTexto
        eventoColor = event
        eventoTexto = event

def guardar_datos(memoria, formato, directory, T_init):
    T_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    T_init_str = T_init.strftime("%Y-%m-%d_%H-%M-%S")
    memoria = pd.DataFrame(memoria)
    memoria = memoria.set_index('time')
    if formato == 'csv':
        memoria.to_csv('{}/{}-{}.csv'.format(directory, T_init_str, T_str))
    elif formato == 'json':
        memoria.to_json('{}/{}-{}.json'.format(directory, T_init_str, T_str))
    else:
        memoria.to_pickle('{}/{}-{}.pkl'.format(directory, T_init_str, T_str))


cliente = Cliente("opc.tcp://localhost:4840/freeopcua/server/", suscribir_eventos=True, SubHandler=SubHandler)
cliente.conectar()

# Aplicación con Dash
colors = {
    'background': '#111111',
    'background-section': '#2B2B2B',
    'text': '#FFD700'
}

app = dash.Dash(external_stylesheets=["https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.3/css/bulma.min.css"])

frecMax = 1


app.layout = html.Div(style={'backgroundColor': colors['background']}, className="container", children=[
    html.Section(className="section", style={'backgroundColor': colors['background']}, children=[
        html.H1('Control Center', className="title has-text-centered", style={'color': colors['text']}),

        # Interval component
        dcc.Interval(id='interval-component', interval=int(1/frecMax*1000), n_intervals=0),
        
        # Live update text
        html.Div(id='live-update-text1', className="has-text-centered", style={'color': colors['text']}),
        html.Br(),

        # First live update graph
        dcc.Graph(id='live-update-graph1'),
        
        # Intermediate data container (hidden)
            html.Div(id='intermediate', style={'display': 'none'}),
            
            # Second live update graph - added directly without additional Div
            dcc.Graph(id='live-update-graph2'),

            # Save section
            html.Div(id='GuardarDiv', className="has-text-centered", style={'color': colors['text'], 'padding': '20px', 'border': '2px solid gold', 'borderRadius': '10px', 'backgroundColor': colors['background-section']}, children=[
                html.H4('Save data', className="has-text-centered is-size-2"),
                html.Div(id='InputMuestrasContainer', children=[
                    html.H4('Number of Samples', className="has-text-centered is-size-4", style={'color': ['text']}),
                    dcc.Input(id='NmuestrasInput', type='number', value=Nmuestras, min=1)
                ]),
                html.Br(),
                dcc.RadioItems(id='Formato', style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center'}, options=[

                    {'label': '.csv    ', 'value': 'csv'},
                    {'label': '.json    ', 'value': 'json'},
                    {'label': '.pickle    ', 'value': 'pickle'}
                ], value='csv', className="columns radio"),
                html.Br(),
                html.Div(id='GuardarContainer', className="columns", style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center'}, children=[
                    html.Button('Save Data', id='guardar', n_clicks=0, className="column is-4 button is-danger", style={'backgroundColor': '#006400', 'border': '2px solid green',  'margin': '0 10px'}),
                    html.Button('Stop Saving', id='Noguardar', n_clicks=0, className="column is-4 button is-danger", style={'backgroundColor': '#FF0000', 'border': '2px solid red', 'margin': '0 10px'})
                ]),
                html.Div(id='indicativoGuardar', children=['Not Saving'], className="has-text-centered is-size-4")
            ]),
            html.Br(),
            # Alarm section
            html.Div(id='AlarmaContainer', className="container", style={'backgroundColor': colors['background-section'], 'padding': '20px', 'border': '2px solid gold', 'borderRadius': '10px', 'color': colors['text']}, children=[
                html.H4('Alarm', className="has-text-centered is-size-2"),
                html.Div(id='Alarma', style={'backgroundColor': 'black'}, children=[
                    html.H2(id='AlarmaTexto', className="title has-text-centered", style={'color': '#FFD700'}, children=['Alarm Inactive'])
                ])
            ]),
            html.Br(),

            # Mode selection
            html.Div(id='Modo', className="container", style={'color': colors['text'], 'padding': '20px', 'border': '2px solid gold', 'borderRadius': '10px', 'backgroundColor': colors['background-section']}, children=[
                html.H4('Controller Mode', className="has-text-centered is-size-2"),
                html.Br(),
                html.H4('Ratio Values', className="has-text-centered is-size-4"),
                html.Div(id='RazonesDiv', className="columns is-centered", children=[
                    html.Div(id='Razon1Div', className="column has-text-centered", children=[
                        html.Label('Ratio 1'),
                        dcc.Slider(id='Razon1', min=0, max=1, step=0.05, value=0.7, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered")
                    ]),
                    html.Div(id='Razon2Div', className="column has-text-centered", children=[
                        html.Label('Ratio 2'),
                        dcc.Slider(id='Razon2', min=0, max=1, step=0.05, value=0.6, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered")
                    ])
                ]),
                # border: 0px;
                # width: 100%;
                # height: 2em;
                    html.Div(id='EleccionDiv', className="control", children=[
                        dcc.RadioItems(id='Eleccion', options=[
                            {'label': 'Manual Mode        ', 'value': 'Manual', 'className': 'radio'},
                            {'label': 'Automatic Mode        ', 'value': 'Automatico', 'className': 'radio'}
                        ], value='Manual', className="columns radio", style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center'}),
                            html.Div(id='MyDiv', className="has-text-centered is-size-4")
                    ]),

                        # Modes section
                    html.Div(id='Modos', className="container",style={'color': colors['text'], 'padding': '20px', 'border': '2px solid gold', 'borderRadius': '10px', 'backgroundColor': colors['background-section']} , children=[
                            # Manual Mode
                            html.Div(id='Manual', className="container", style={'color': colors['text'], 'background-color': 'black', 'border': '2px solid gray'}, children=[
                            html.H4('Manual Mode', className="has-text-centered is-size-2"),
                            html.Br(),
                            dcc.RadioItems(id='TipoManual', options=[
                                {'label': 'Fixed Value        ', 'value': 'fijo'},
                                {'label': 'Sine Wave        ', 'value': 'sinusoide'}
                            ], value='fijo', className="columns radio", style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center'} ),

                            # Sine wave settings
                            html.Div(id='SineWaveDiv', className="columns is-centered", children=[
                                html.H4('Sine Wave', className="has-text-centered is-size-4"),
                                html.Div(id='Frec', className="column has-text-centered", children=[
                                    html.Label('Freq'),
                                    dcc.Slider(id='FrecSlider', min=frecMax/25, max=frecMax/2, step=0.5, value=frecMax/4, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered")
                                ]),
                                html.Div(id='Amp', className="column has-text-centered", children=[
                                    html.Label('Amp'),
                                    dcc.Slider(id='AmpSlider', min=0.1, max=1, step=0.5, value=1, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered")
                                ]),
                                html.Div(id='Fase', className="column has-text-centered", children=[
                                    html.Label('Phase'),
                                    dcc.Slider(id='FaseSlider', min=0, max=6.28, step=0.5, value=0, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered")
                                ]),
                                html.Div(id='Offset', className="column has-text-centered", children=[
                                    html.Label('Offset'),
                                    dcc.Slider(id='OffsetSlider', min=-1, max=1, step=0.5, value=0, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered")
                                ])
                            ]),
                            html.Div(id='Sliders2', className="columns is-centered", children=[
                            # Fixed value input
                            html.Br(),
                            html.H4('Fixed Value for Tank 1', className="has-text-centered is-size-4"),
                            html.Div(className="has-text-centered", children=[
                                dcc.Slider(id='ManualFijo1', min=0.1, max=1, step=0.01, value=0.5, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered")
                            ]),
                            html.Br(),
                            html.H4('Fixed Value for Tank 2', className="has-text-centered is-size-4"),
                            html.Div(className="has-text-centered", children=[
                                dcc.Slider(id='ManualFijo2', min=0.1, max=1, step=0.01, value=0.3, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered")
                        ])
                    ])
                    ]),

                        # Automatic Mode
                        html.Div(id='Automatico', className="container", style={'color': colors['text'], 'background-color': 'black', 'border': '2px solid gray'}, children=[
                            html.H4('PID Constants', className="has-text-centered is-size-2"),
                            html.Div(id='constantes_controladores', className="columns is-centered", children=[
                                    html.Div(id='P1', className="column", children=[
                                        html.H4('Tank 1', className="has-text-centered is-size-4"),
                                        html.H4('SetPoint Tank 1', className="has-text-centered"),
                                        dcc.Slider(id='SPT1', min=0, max=100, step=0.5, value=12, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered"),
                                        html.H4('Proportional (Kp1)', className="has-text-centered"),
                                        dcc.Slider(id='Kp1', min=0, max=100, step=0.5, value=1, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered"),
                                        html.H4('Integral (Ki1)', className="has-text-centered"),
                                        dcc.Slider(id='Ki1', min=0, max=10, step=0.1, value=0, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered"),
                                        html.H4('Derivative (Kd1)', className="has-text-centered"),
                                        dcc.Slider(id='Kd1', min=0, max=100, step=0.5, value=0, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered"),
                                        html.H4('Anti wind-up (Kw1)', className="has-text-centered"),
                                        dcc.Slider(id='Kw1', min=0, max=10, step=0.01, value=0, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered"),
                                        html.H4('D filter const. (Tf1)', className="has-text-centered"),
                                        dcc.Slider(id='Tf1', min=0, max=100, step=0.5, value=0, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered"),
                                ]),
                                    html.Div(id='P2', className="column", children=[
                                        html.H1('Tank 2', className="has-text-centered is-size-4"),
                                        html.H4('SetPoint Tank 2', className="has-text-centered"),
                                        dcc.Slider(id='SPT2', min=0, max=100, step=0.5, value=13, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered"),
                                        html.H4('Proportional (Kp2)', className="has-text-centered"),
                                        dcc.Slider(id='Kp2', min=0, max=100, step=0.5, value=1, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered"),
                                        html.H4('Integral (Ki2)', className="has-text-centered"),
                                        dcc.Slider(id='Ki2', min=0, max=10, step=0.1, value=0, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered"),
                                        html.H4('Derivative (Kd2)', className="has-text-centered"),
                                        dcc.Slider(id='Kd2', min=0, max=100, step=0.5, value=0, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered"),
                                        html.H4('Anti wind-up (Kw2)', className="has-text-centered"),
                                        dcc.Slider(id='Kw2', min=0, max=10, step=0.01, value=0, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered"),
                                        html.H4('D filter const. (Tf2)', className="has-text-centered"),
                                        dcc.Slider(id='Tf2', min=0, max=100, step=0.5, value=0, marks=None, tooltip={"placement": "bottom"}, className="column has-text-centered")
                                ])
                            ])
                        ])
                    ]),
            ]),
            html.Br(),

    ])
])


app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Centro de control del Grupo 2</title>
        {%favicon%}
        {%css%}
        <style>
            html, body {
                background-color: #111111;
                margin: 0;
                height: 100%;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''


# Callback para alternar entre modos 
@app.callback(
    [Output('Manual', 'style'), Output('Automatico', 'style')],
    [Input('Eleccion', 'value')]
)
def toggle_mode(mode):
    if mode == 'Manual':
        return {'display': 'block'}, {'display': 'none'}
    elif mode == 'Automatico':
        return {'display': 'none'}, {'display': 'block'}
    return {'display': 'none'}, {'display': 'none'}

# Callback para alternar entre modos de control manual
@app.callback(
    [Output('SineWaveDiv', 'style'), Output('Sliders2', 'style')],
    [Input('TipoManual', 'value')]
)
def toggle_manual_mode(mode):
    if mode == 'sinusoide':
        return {'display': 'block'}, {'display': 'none'}
    elif mode == 'fijo':
        return {'display': 'none'}, {'display': 'block'}
    return {'display': 'none'}, {'display': 'none'}


################################################## Alarma ############################################################
@app.callback(Output('Alarma', 'style'), [Input('interval-component', 'n_intervals')])
def Alarma(n):
    global eventoColor
    if eventoColor != 0:
        style = {'backgroundColor': '#FF0000', 'padding': '10px', 'border': '2px solid red', 'borderRadius': '10px'}
    else:
        style = {'backgroundColor': '#006400', 'padding': '10px', 'border': '2px solid green', 'borderRadius': '10px'}
    eventoColor = 0
    return style

@app.callback(Output('AlarmaTexto', 'children'), [Input('interval-component', 'n_intervals')])
def TextoAlarma(n):
    global eventoTexto
    if eventoTexto != 0:
        mensaje =eventoTexto.Message.Text.split(':')
        res = '{}: {}'.format(mensaje[1], round(float(mensaje[2]), 2))
    else:
        res = 'Inactive'
    eventoTexto = 0
    return res

################################################## Guardar ###########################################################
nGuardar_ant = 0
nNoGuardar_ant = 0


@app.callback(Output('indicativoGuardar', 'children'), [Input('guardar', 'n_clicks'),Input('Noguardar', 'n_clicks')])
def Guardar(nGuardar, nNoGuardar):
    global nGuardar_ant, nNoGuardar_ant

    if nGuardar_ant != nGuardar:
        nGuardar_ant = nGuardar
        return 'Saving...'
    elif nNoGuardar_ant != nNoGuardar:
        return 'Not Saving'
    else:
        return 'Not Saving'




#################################################### Supervisión ######################################################
# Se guardan los valores
@app.callback(Output('intermediate', 'children'), [Input('interval-component', 'n_intervals')])
def UpdateInfo(n):
    global evento
    h1 = cliente.alturas['H1'].get_value()
    h2 = cliente.alturas['H2'].get_value()
    h3 = cliente.alturas['H3'].get_value()
    h4 = cliente.alturas['H4'].get_value()
    alturas = {'h1':h1, 'h2': h2, 'h3': h3, 'h4': h4}
    return json.dumps(alturas)

# Se actualiza el texto
@app.callback(Output('live-update-text1', 'children'), [Input('intermediate', 'children')])
def UpdateText(alturas):
    alturas = json.loads(alturas)
    style = {'padding': '15px', 'fontSize': '20px', 'border': '2px solid powderblue', 'backgroundColor': colors['background-section']}
    return [
        html.Span('Tank 1: {}'.format(round(alturas['h1'], 2)), style=style),
        html.Span('Tank 2: {}'.format(round(alturas['h2'], 2)), style=style),
        html.Span('Tank 3: {}'.format(round(alturas['h3'], 2)), style=style),
        html.Span('Tank 4: {}'.format(round(alturas['h4'], 2)), style=style)
    ]

times = deque(maxlen=100)
h1 = deque(maxlen=100)
h2 = deque(maxlen=100)
h3 = deque(maxlen=100)
h4 = deque(maxlen=100)
V1 = deque(maxlen=100)
V2 = deque(maxlen=100)
# Valores de los estanques
@app.callback(Output('live-update-graph1', 'figure'),
               [Input('intermediate', 'children')],
               [State('Eleccion', 'value'),
               State('SPT1', 'value'),
                State('SPT2', 'value')])
def UpdateGraph(alturas, eleccion, SPT1, SPT2):
    global times, h1,h2,h3,h4
    alturas = json.loads(alturas)
    times.append(datetime.datetime.now())
    # Alturas
    h1.append(alturas['h1'])
    h2.append(alturas['h2'])
    h3.append(alturas['h3'])
    h4.append(alturas['h4'])

    plot1 = go.Scatter(x=list(times), y=list(h1), name='Tanque1', mode='lines+markers')
    plot2 = go.Scatter(x=list(times), y=list(h2), name='Tanque2', mode='lines+markers')
    plot3 = go.Scatter(x=list(times), y=list(h3), name='Tanque3', mode='lines+markers')
    plot4 = go.Scatter(x=list(times), y=list(h4), name='Tanque4', mode='lines+markers')

    fig = plotly.tools.make_subplots(rows=2, cols=2, vertical_spacing=0.2,
                                     subplot_titles=('Tanque3', 'Tanque4', 'Tanque1', 'Tanque2'), print_grid=False)


    #fig['layout'].update(height=600, width=1300, title='Niveles de los Tanques')
    fig.append_trace(plot1, 2, 1)
    fig.append_trace(plot2, 2, 2)
    fig.append_trace(plot3, 1, 1)
    fig.append_trace(plot4, 1, 2)


    if eleccion == 'Automatico':
        try:
            sp1_value = float(SPT1)
            sp2_value = float(SPT2)

            # Correct x values for setpoint lines:
            sp1_plot = go.Scatter(x=list(times), y=[sp1_value] * len(list(times)), 
                                 name='SetPoint Tanque 1', line=dict(color='red', dash='dash'))
            sp2_plot = go.Scatter(x=list(times), y=[sp2_value] * len(list(times)), 
                                 name='SetPoint Tanque 2', line=dict(color='red', dash='dash'))

            fig.add_trace(sp1_plot, row=2, col=1)
            fig.add_trace(sp2_plot, row=2, col=2)

        except ValueError:
            print("Invalid SetPoint values. Please enter numbers.")


    fig.update_layout(margin={'l': 30, 'r': 10, 'b': 30, 't': 30},
                      legend={'x': 0, 'y': 1, 'xanchor': 'left'},
                      plot_bgcolor=colors['background'],
                      paper_bgcolor=colors['background'],
                      font={'color': colors['text']})

    return fig

################################################# Control ##############################################################

@app.callback(
    Output(component_id='MyDiv', component_property='children'),
    [Input(component_id='Eleccion', component_property='value')]
)
def update_output_div(input_value):
    return 'Selected mode: {}'.format(input_value)

#################### Modo Manual ##################################
@app.callback(Output('1', 'children'), [Input('FrecSlider', 'value')])
def ActualizaLabels1(n):
    return 'Frec: {} Hz'.format(n)
@app.callback(Output('2', 'children'), [Input('AmpSlider', 'value')])
def ActualizaLabels2(n):
    return 'Amp: {}'.format(n)
@app.callback(Output('3', 'children'), [Input('FaseSlider', 'value')])
def ActualizaLabels3(n):
    return 'Fase: {}'.format(n)
@app.callback(Output('4', 'children'), [Input('OffsetSlider', 'value')])
def ActualizaLabels4(n):
    return 'Offset: {}'.format(n)
@app.callback(Output('Razon1Label', 'children'), [Input('Razon1', 'value')])
def ActualizaRazon1(value):
    return 'Razon 1: {}'.format(value)
@app.callback(Output('Razon2Label', 'children'), [Input('Razon2', 'value')])
def ActualizaRazon1(value):
    return 'Razon 2: {}'.format(value)


#################### Modo Automático ##############################

# PIDS
pid1 = G2_PID()
pid2 = G2_PID()

times_list = deque(maxlen=100)
v1_list = deque(maxlen=100)
v2_list = deque(maxlen=100)
t = 0

memoria = []
T_init = 0

@app.callback(Output('live-update-graph2', 'figure'),
              [Input('intermediate', 'children')],
              [State('Eleccion', 'value'), State('TipoManual', 'value'),
                State('FrecSlider', 'value'),State('AmpSlider', 'value'),
                State('OffsetSlider', 'value'),State('FaseSlider', 'value'),
                State('ManualFijo1', 'value'), State('ManualFijo2', 'value'), State('Kp1', 'value'),
                State('Ki1', 'value'), State('Kd1', 'value'), State('Kw1','value'),
                State('Kp2', 'value'), State('Ki2', 'value'), State('Kd2', 'value'), State('Kw2','value'),
                State('Tf1', 'value'), State('Tf2', 'value'),
                State('SPT1', 'value'), State('SPT2', 'value'),
                State('indicativoGuardar', 'children'), State('Formato', 'value'),
                State('Razon1', 'value'), State('Razon2', 'value')])
def SalidaControlador(alturas, eleccion, tipoManual, frec, amp, offset, fase, manualFijo1, manualFijo2,
                      Kp1, Ki1, Kd1, Kw1, Tf1, Kp2, Ki2, Kd2, Kw2, Tf2, SPT1, SPT2, guardando, formato, razon1, razon2):
    global times_list, v1_list, v2_list, t, pid1, pid2, memoria, T_init, nGuardar_ant, nNoGuardar_ant, Nmuestras
    alturas = json.loads(alturas)
    T = datetime.datetime.now()
    v1 = v2 = 0
    cliente.razones['razon1'].set_value(razon1)
    cliente.razones['razon2'].set_value(razon2)
    # Si se elige la sinusoide
    if eleccion == 'Manual' and tipoManual == 'sinusoide':
        v1 = amp*np.cos(2*np.pi*frec*t + fase) + offset
        v2 = amp*np.cos(2*np.pi*frec*t + fase) + offset
        t += 1/frecMax
        v1 = v1 if v1 > 0 else 0
        v2 = v2 if v2 > 0 else 0

    # Si se elige el valor fijo
    elif eleccion == 'Manual' and tipoManual == 'fijo':
        v1 = float(manualFijo1)
        v2 = float(manualFijo2)

    # Modo automático
    elif eleccion == 'Automatico':
        # SetPoints
        pid1.setPoint = float(SPT1)
        pid2.setPoint = float(SPT2)

        # Constantes
        pid1.set_PID_param(float(Kp1), float(Ki1), float(Kd1), float(Tf1), float(Kw1))
        pid2.set_PID_param(float(Kp2), float(Ki2), float(Kd2), float(Tf2), float(Kw2))

        v1 = pid1.update(alturas['h1'])
        v2 = pid2.update(alturas['h2'])

    # Guardando
    if guardando == 'Saving...':
        if memoria == []:
            T_init = datetime.datetime.now()

        if eleccion == 'Manual':
            memoria.append({'time':T,'h1': alturas['h1'], 'h2': alturas['h2'], 'h3': alturas['h3'], 'h4': alturas['h4'],
                            'v1': v1, 'v2':v2, 'modo': '{}-{}'.format(eleccion, tipoManual), 'razon1': float(razon1), 'razon2': float(razon2)})
        else:
            memoria.append(
                {'time': T, 'h1': alturas['h1'], 'h2': alturas['h2'], 'h3': alturas['h3'], 'h4': alturas['h4'],
                 'v1': v1, 'v2': v2, 'modo': '{}'.format(eleccion), 'sp1': float(SPT1), 'sp2': float(SPT2),
                 'Ki1': float(Ki1),'Kd1': float(Kd1),'Kp1': float(Kp1),'Kw1': float(Kw1), 'Tf1': float(Tf1),
                 'Ki2': float(Ki2), 'Kd2': float(Kd2), 'Kp2': float(Kp2), 'Kw2': float(Kw2), 'Tf2': float(Tf2), 'razon1': float(razon1), 'razon2': float(razon2)})
        # if len(memoria) > Nmuestras:
        #     guardar_datos(memoria, formato, directory, T_init)

    if (guardando == 'Not Saving' and memoria != []):

        guardar_datos(memoria, formato, directory, T_init)
        memoria = []
        
    cliente.valvulas['valvula1'].set_value(v1)
    cliente.valvulas['valvula2'].set_value(v2)
    times_list.append(T)
    v1_list.append(v1)
    v2_list.append(v2)

    plot1 = go.Scatter(x=list(times_list), y=list(v1_list), name='Valvula1', mode='lines+markers')
    plot2 = go.Scatter(x=list(times_list), y=list(v2_list), name='Valvula2', mode='lines+markers')


    fig = plotly.tools.make_subplots(rows=1, cols=2,
                                     subplot_titles=('Valvula1', 'Valvula2'), print_grid=False)
    fig['layout']['margin'] = {
        'l': 30, 'r': 10, 'b': 200, 't': 30
    }
    fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}
    fig['layout']['plot_bgcolor'] = colors['background']
    fig['layout']['paper_bgcolor'] = colors['background']
    fig['layout']['font']['color'] = colors['text']

    #fig['layout'].update(height=300, width=1300, title='Niveles de los Tanques')
    fig.append_trace(plot1, 1, 1)
    fig.append_trace(plot2, 1, 2)

    return fig


app.run_server()
