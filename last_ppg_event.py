import arcpy
import numpy as np
import pandas as pd

arcpy.env.overwriteOutput=1
arcpy.env.workspace = r"C:/Python_proj/dane/"
path = "C:/Python_proj/dane/"
result_path = path+"wyniki/"
file = "BUBD.shp"


" ---------- FUNKCJE ----------- "
"1"
def segment_length(col_x, col_y, value1, value2):
    "col_x, col_y - kolumny z wartosciami X i Y, value1=1 dla dlugosci segmentu 'przed', value1=-1 dla segmentu 'po'"
    "col_x i col_y to kolumny DataFrame"
    length = np.sqrt((col_x.shift(value1) - col_x.shift(value2))**2 + (col_y.shift(value1) - col_y.shift(value2))**2)
    return length
"2"
def vertex_angle(col_x, col_y):
    "col_x i col_y to kolumny DataFrame"
    "obliczenie katow z roznicy azymutow"
    deltaX1 = col_x.shift(-1) - col_x
    deltaY1 = col_y.shift(-1) - col_y
    dir1 = np.arctan2(deltaX1, deltaY1) * 180 / np.pi
    dir1 = dir1.where(dir1 > 0, dir1 + 360).fillna(dir1[0])

    deltaX2 = col_x.shift(1) - col_x
    deltaY2 = col_y.shift(1) - col_y
    dir2 = np.arctan2(deltaX2, deltaY2) * 180 / np.pi
    dir2 = dir2.where(dir2 > 0, dir2 + 360)
    dir2 = dir2.fillna(dir2.iloc[-1])

    angle = dir2 - dir1
    angle = angle.where(angle > 0, angle + 360)
    return angle
"3"
def is_node(budynki):
    "budynki - plik poligonow - oryginalny BUBD.shp"
    wierzcholki = result_path + "wierzcholki.shp"
    if arcpy.Exists(wierzcholki):
        arcpy.Delete_management(wierzcholki)
    "zamiana poligonow na wierzcholki"
    arcpy.FeatureVerticesToPoints_management(budynki, wierzcholki)

    cursor = arcpy.da.SearchCursor(result_path + "wierzcholki.shp", ['FID', 'gmlId', 'SHAPE@XY'])
    vertic_coords = [(row[0], row[1], row[2][0], row[2][1]) for row in cursor]
    neighbour_vertex = []
    for coord1 in vertic_coords:
        for coord2 in vertic_coords:
            "porownywanie wspolrzednych i gmlid dla poszczegolnych punktow"
            if (coord1[1]) != coord2[1] and (coord1[2] == coord2[2]) and (coord1[3] == coord2[3]):
                # print coord1[0], coord2[0], " - wierzcholki sasiedztwa"
                neighbour_vertex.append(coord1[0])
    return len(neighbour_vertex)
#all_vert = is_node(path+file)
#print(all_vert)
# wyszlo 9726 wierzcholkow sasiedztwa
"4"
def deflection(vertices_class, mbg):
    "odleglosc do linii"
    arcpy.Near_analysis(vertices_class, mbg)
    "wybranie kolumny z odlegloscia i zapisanie jej do obiektu Series"
    cursor = arcpy.da.SearchCursor(vertices_class, ["NEAR_DIST"])
    list = [row[0] for row in cursor]
    del row, cursor
    distance = pd.Series(list)
    return distance
"5"
def intersect(data_path):
    cursor = arcpy.da.SearchCursor(data_path, "TYPE")
    lst = [row for row in cursor]
    lista = []
    for l in lst:
        for l2 in lst:
            lista.append("{0}_{1}".format(l[0], l2[0]))
    id = pd.Series(lista)

    elements = arcpy.CopyFeatures_management(data_path, arcpy.Geometry())
    DE_9IM = {}
    DE_9IM["ID"] = id
    Contains = [element1.contains(element2) for element1 in elements for element2 in elements]
    DE_9IM["contains"] = pd.Series(Contains)
    Crosses = [element1.crosses(element2) for element1 in elements for element2 in elements]
    DE_9IM["crosses"] = pd.Series(Crosses)
    Disjoint = [element1.disjoint(element2) for element1 in elements for element2 in elements]
    DE_9IM["disjoint"] = pd.Series(Disjoint)
    Equals = [element1.equals(element2) for element1 in elements for element2 in elements]
    DE_9IM["equals"] = pd.Series(Equals)
    Overlaps = [element1.overlaps(element2) for element1 in elements for element2 in elements]
    DE_9IM["overlaps"] = pd.Series(Overlaps)
    Touches = [element1.touches(element2) for element1 in elements for element2 in elements]
    DE_9IM["touches"] = pd.Series(Touches)
    Within = [element1.within(element2) for element1 in elements for element2 in elements]
    DE_9IM["within"] = pd.Series(Within)

    IntersectMatrix = pd.DataFrame(DE_9IM)
    print("Wynik z macierzy intersekcji")
    print IntersectMatrix

"sprawdzenie (na danych testowych), czy funkcja dziala poprawnie"
#intersect("C:\Python_proj\dane\Dane.mdb\Test\polygon")
"6"
def minimal_geometry(in_feature):
    "dane wejsciowe: in_feature - budynek w .shp"
    MBG_list = ["RECTANGLE_BY_AREA", "RECTANGLE_BY_WIDTH", "CONVEX_HULL", "CIRCLE","ENVELOPE"]
    for mbg in MBG_list:
        arcpy.MinimumBoundingGeometry_management(in_feature, result_path+mbg+".shp", mbg)
        "zamiana na linie"
        arcpy.PolygonToLine_management(result_path+mbg+".shp", result_path+'{0}_line.shp'.format(mbg), "IGNORE_NEIGHBORS")
        "usuniecie niepotrzebnej juz warstwy"
        arcpy.Delete_management(result_path+mbg+".shp")

" -------------------- FUNKCJE POMOCNICZE (JAKO CZESC ZADANIA EGZAMINACYJNEGO)-------------------- "
"funkcja wybierajaca dany budynek z pliku BUBD.shp"
def select(table, value):
    "table - oryginalny BUBD.shp, value - identyfikator gmlId"
    arcpy.MakeFeatureLayer_management(table, "lyr{0}".format(value))
    selection = arcpy.SelectLayerByAttribute_management("lyr{0}".format(value), "NEW_SELECTION", "gmlId = '{0}'".format(value))
    return selection

def length_in_out_angle(results):
    "results - DataFrame zawierajacy kolumny X i Y wierzcholkow konkretnego budynku"
    "obliczenie dla kazdego punktu dlugosci segmentu 'przed' "
    results['length_in'] = segment_length(results['X'], results['Y'], 1, 0)
    "pierwszy punkt z ostatnim sie pokrywaja (sa takie same), dlatego przypisano mu wartosc dla punktu pierwszego"
    results['length_in'] = results.length_in.fillna(results['length_in'].iloc[-1])

    "obliczenie dla kazdego punktu dlugosci segmentu 'po' "
    results['length_out'] = segment_length(results['X'], results['Y'], -1, 0)
    "pierwszy punkt z ostatnim sie pokrywaja (sa takie same), dlatego przypisano mu wartosc dla punktu pierwszego"
    results['length_out'] = results.length_out.fillna(results['length_out'].iloc[0])
    "obliczenie kata wewnetrznego"
    results['angle_in'] = vertex_angle(results['X'], results['Y'])
    "jako wynik powstaje DataFrame wzbogacony o dodatkowe kolumny"
    return results

" -------------------- LISTA BUDYNKOW -------------------- "
"lista z gmlId budynku"
"lista z wybranymi budynkami"
building_id = ["PL.PZGIK.BDOT10k.BUBDA.18.6325983", "PL.PZGIK.BDOT10k.BUBDA.18.6319873"]
#lista z wszystkimi budynkami w pliku
#building_id = [str(line.getValue("gmlId")) for line in arcpy.SearchCursor(file)]

" -------------------- ZADANIE EGZAMINACYJNE - WLASCIWY PROGRAM -------------------- "
"slownik z minimalnymi geometriami"
min_geom = {"RECTANGLE_BY_AREA": result_path+'RECTANGLE_BY_AREA_line.shp',
            "RECTANGLE_BY_WIDTH": result_path+'RECTANGLE_BY_WIDTH_line.shp',
            "CONVEX_HULL": result_path+'CONVEX_HULL_line.shp',
            "CIRCLE": result_path+'CIRCLE_line.shp',
            "ENVELOPE": result_path+'ENVELOPE_line.shp'}

"DataFrame na wszystkie wyniki"
results_all = pd.DataFrame()
start = 0
cursor = arcpy.SearchCursor(file)
for row in cursor:
    buildings = {}
    "pobranie wartosci z kolumny z identyfiaktorem z pliku BUBD.shp"
    value = str(row.getValue("gmlId"))
    if value in building_id:
        selection = select(file, value)
        bldg_id = value.split('.')[-1]
        "zapisanie wierzcholkow budynku do pliku (plik z punktami) o nazwie 'result_ostatni_elem_identyf_gmlId.shp' "
        buildings['bldg_{0}'.format(bldg_id)] = arcpy.FeatureVerticesToPoints_management(selection, result_path+"result_{0}.shp".format(bldg_id))

        for id_bud, vertices_bud in buildings.items():
            "utworzenie DataFrame do zapisu danych o punktach"
            results = pd.DataFrame()
            cursor = arcpy.da.SearchCursor(vertices_bud, ['FID', 'gmlId', 'SHAPE@XY'])
            "iteracja przez kolejne punkty"
            for row in cursor:
                point_id = row[0]
                "dla ostatniego wierzcholka, nastepny wierzcholek to ten z id=0"
                if point_id == int(arcpy.GetCount_management(vertices_bud).getOutput(0))- 1:
                    next_point = 0
                else:
                    next_point = point_id + 1
                identyfikator_bud = row[1]
                coordX = row[2][0]
                coordY = row[2][1]

                "dopisanie kolejnych wierszy do DataFrame"
                results = results.append(
                    pd.Series(data=[int(point_id), identyfikator_bud, int(next_point), coordX, coordY], name=row[0],
                              index=['Id_pkt', 'Identyfikator_budynku', 'Nr_kolejnego_wierzcholka', 'X', 'Y']))

            "dolaczenie atrybutow length_in, length_out, angle_in"
            length_in_out_angle(results)
            "ponizsza funkcja tworzy liste minimalnych geometrii dla budynku"
            minimal_geometry(vertices_bud)
            "iteracja przez slownik - nazwa: MBG"
            for name, mbg in min_geom.items():
                results["Strzalka_{0}".format(name)] = deflection(vertices_bud, mbg)
                "usuniecie niepotrzebnych juz warstw"
                arcpy.Delete_management(mbg)
            arcpy.Delete_management(vertices_bud)

            results_all = results_all.append(results)
        "informacja, ze dla danego budynku wykonano obliczenia"
        start += 1
        print(start, "- ok")

results_all.to_csv(result_path+"results.csv")









