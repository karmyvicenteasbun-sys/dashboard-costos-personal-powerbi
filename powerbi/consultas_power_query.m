// =====================================================================
// Carga de datos en Power Query (Power BI Desktop)
// ---------------------------------------------------------------------
// 1) Crear el parámetro RutaDatos:
//    Inicio > Transformar datos (abre Power Query) > Administrar parámetros
//    > Nuevo parámetro. Nombre: RutaDatos | Tipo: Texto
//    Valor actual: la carpeta "datos" del repositorio, terminada en barra.
//    Ejemplo: C:\Proyectos\dashboard-costos-personal-powerbi\datos\
//
// 2) Crear dos consultas en blanco (Nuevo origen > Consulta en blanco >
//    Editor avanzado) y pegar en cada una el código de abajo.
//    Nombres: Colaboradores y Planilla.
//
// Los tipos se convierten con la cultura "en-US" porque los CSV usan punto
// decimal; así no importa la configuración regional de la computadora.
// =====================================================================


// ---------------------------------------------------------------------
// Consulta: Colaboradores   (dimensión: una fila por persona)
// ---------------------------------------------------------------------
let
    Origen = Csv.Document(
        File.Contents(RutaDatos & "colaboradores.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    // Las personas activas no tienen fecha ni tipo de egreso: vacío -> null
    VaciosANull = Table.ReplaceValue(
        Encabezados, "", null, Replacer.ReplaceValue, {"fecha_egreso", "tipo_egreso"}
    ),
    Tipos = Table.TransformColumnTypes(
        VaciosANull,
        {
            {"id_colaborador", type text},
            {"area", type text},
            {"cargo", type text},
            {"nivel", type text},
            {"turno", type text},
            {"fecha_ingreso", type date},
            {"fecha_egreso", type date},
            {"tipo_egreso", type text},
            {"edad_ingreso", Int64.Type},
            {"distancia_km", type number},
            {"compa_ratio", type number},
            {"evaluacion_desempeno", Int64.Type},
            {"haber_basico_actual_bs", type number}
        },
        "en-US"
    ),
    Estado = Table.AddColumn(
        Tipos, "estado", each if [fecha_egreso] = null then "Activo" else "Egresado", type text
    )
in
    Estado


// ---------------------------------------------------------------------
// Consulta: Planilla   (hechos: una fila por persona y mes)
// ---------------------------------------------------------------------
let
    Origen = Csv.Document(
        File.Contents(RutaDatos & "planilla_mensual.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(
        Encabezados,
        {
            {"periodo", type text},
            {"fecha_periodo", type date},
            {"id_colaborador", type text},
            {"dias_trabajados", Int64.Type},
            {"dias_ausencia", Int64.Type},
            {"horas_extra", type number},
            {"haber_basico_bs", Currency.Type},
            {"basico_pagado_bs", Currency.Type},
            {"bono_antiguedad_bs", Currency.Type},
            {"monto_horas_extra_bs", Currency.Type},
            {"total_ganado_bs", Currency.Type},
            {"aportes_patronales_bs", Currency.Type},
            {"provision_aguinaldo_bs", Currency.Type},
            {"provision_indemnizacion_bs", Currency.Type},
            {"costo_total_bs", Currency.Type}
        },
        "en-US"
    )
in
    Tipos
