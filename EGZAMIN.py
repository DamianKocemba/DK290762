import arcpy
import numpy as np
import pandas as pd
" -------------------- FUNKCJE -------------------- "
def segment_length(col_x, col_y, value1, value2):
    "col_x, col_y - kolumny z wartosciami X i Y, value1=1 dla dlugosci segmentu 'przed', value1=-1 dla segmentu 'po'"
    "col_x i col_y to kolumny DataFrame"
    col_x, col_y = col_x.astype(float), col_y.astype(float)
    length = np.sqrt((col_x.shift(value1) - col_x.shift(value2))**2 + (col_y.shift(value1) - col_y.shift(value2))**2)
    return length

def vertex_angle(col_x, col_y):
    "col_x i col_y to kolumny DataFrame"
    "obliczenie katow z roznicy azymutow"
    col_x, col_y = col_x.astype(float), col_y.astype(float)
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


def minimal_geometry(in_feature):
    "dane wejsciowe: in_feature - budynek w .shp"
    MBG_list = ["RECTANGLE_BY_AREA", "RECTANGLE_BY_WIDTH", "CONVEX_HULL", "CIRCLE","ENVELOPE"]
    for mbg in MBG_list:
        arcpy.MinimumBoundingGeometry_management(in_feature, result_path+mbg+".shp", mbg)
        "zamiana na linie"
        arcpy.PolygonToLine_management(result_path+mbg+".shp", result_path+'{0}_line.shp'.format(mbg), "IGNORE_NEIGHBORS")
        "usuniecie niepotrzebnej juz warstwy"
        arcpy.Delete_management(result_path+mbg+".shp")

def deflection(vertices, near_features, name):
    "odleglosc do linii"
    arcpy.Near_analysis(vertices, near_features)
    "wybranie kolumny z odlegloscia i zapisanie jej do obiektu Series"
    cursor = arcpy.SearchCursor(vertices)
    list = [row.getValue("NEAR_DIST") for row in cursor]
    distance = pd.Series(list, name=name)
    return distance

" -------------------- FUNKCJE POMOCNICZE -------------------- "
"funkcja wybierajaca dany budynek z pliku po wartosci gmlid"
def select(in_feature, value):
    "in_feature - sciezka do pliku z wierzcholkami lub MBG; value - identyfikator gmlId"
    name = in_feature.split("/")[-1].split(".")[0]
    arcpy.MakeFeatureLayer_management(in_feature, "lyr_{0}".format(name))
    arcpy.SelectLayerByAttribute_management("lyr_{0}".format(name), "NEW_SELECTION", "gmlId = '{0}'".format(value))
    #zapis warstwy do .shp
    #arcpy.CopyFeatures_management("lyr_{0}".format(name), path+"selekcja_{0}_{1}".format(value.split(".")[-1], name))
    return "lyr_{0}".format(name)

def length_in_out_angle(results):
    "results - DataFrame zawierajacy kolumny X i Y wierzcholkow konkretnego budynku"
    "obliczenie dla kazdego punktu dlugosci segmentu 'przed' "
    results['length_in'] = segment_length(results['X'], results['Y'], 1, 0)
    "pierwszy punkt z ostatnim sie pokrywaja (sa takie same), dlatego przypisano mu wartosc dla punktu ostatniego"
    results['length_in'] = results.length_in.fillna(results['length_in'].iloc[-1])

    "obliczenie dla kazdego punktu dlugosci segmentu 'po' "
    results['length_out'] = segment_length(results['X'], results['Y'], -1, 0)
    "pierwszy punkt z ostatnim sie pokrywaja (sa takie same), dlatego przypisano mu wartosc dla punktu pierwszego"
    results['length_out'] = results.length_out.fillna(results['length_out'].iloc[0])

    "obliczenie kata wewnetrznego"
    results['angle_in'] = vertex_angle(results['X'], results['Y'])
    results['angle_in'] = results.angle_in.fillna(results['angle_in'].iloc[0])

    "jako wynik powstaje DataFrame wzbogacony o dodatkowe kolumny"
    return results

" -------------------- DEKLARACJA ZMIENNYCH -------------------- "
arcpy.env.overwriteOutput=1
arcpy.env.workspace = r"C:/Python_proj/dane2/"
path = "C:/Python_proj/dane2/"
result_path = path+"wyniki/"
file = "BUBD.shp"

"lista z gmlId budynku"
building_id = ["PL.PZGIK.BDOT10k.BUBDA.18.6325841", "PL.PZGIK.BDOT10k.BUBDA.18.6313904"]
#building_id = [str(line.getValue("gmlId")) for line in arcpy.SearchCursor(file)]

" -------------------- WLASCIWY PROGRAM -------------------- "
wierzcholki = result_path+"wierzcholki.shp"
"zamiana BUBD na wierzcholki"
#arcpy.FeatureVerticesToPoints_management(path+file, wierzcholki)
"utworzenie MBG"
#minimal_geometry(path+file)

#arcpy.Near_analysis(wierzcholki, result_path+'ENVELOPE_line.shp')



"slownik z minimalnymi geometriami"
min_geom = {"RectangleByArea": result_path+'RECTANGLE_BY_AREA_line.shp',
            "RectangleByWidth": result_path+'RECTANGLE_BY_WIDTH_line.shp',
            "ConvexHull": result_path+'CONVEX_HULL_line.shp',
            "Circle": result_path+'CIRCLE_line.shp',
            "Envelope": result_path+'ENVELOPE_line.shp'}

"DataFrame na wszystkie wierzcholki budynkow"
buildings = pd.DataFrame()
start = 0
"iteracja po liscie z gmlId"
for gmlid in building_id:
    name = gmlid.split(".")[-1]
    cursor = arcpy.da.SearchCursor(wierzcholki, ["FID", "gmlId", "SHAPE@XY"])
    "DataFrame na wierzcholki z jednego, konkretnego budynku"
    result = pd.DataFrame()
    "znalezienie w pliku z wierzcholkami, wszystkich wierzcholkow dla danego budynku i pobranie informacji"
    vertex = -1
    for row in cursor:
        if row[1] == gmlid:
            vertex = vertex + 1
            result = result.append(pd.DataFrame(data=[row[0], row[1], vertex, row[2][0], row[2][1]],
                               index=["FID", "ID_budynku", "Wierzcholek", "X", "Y"]).T)
    "ponizsza funkcja dodaje do DataFrame kolumny length_in, length_out, angle_in"
    length_in_out_angle(result)
    "wybranie wierzcholkow dane budynku z calego pliku"
    vertices = select(wierzcholki, gmlid)
    "DataFrame na strzalki"
    strzalki = pd.DataFrame()
    "iteracja przez slownik z minimalna geometria"
    for name, mbg in min_geom.items():
        near_features = select(mbg, gmlid)
        "obliczenie strzalek do poszczegolnych MBG"
        strzalka = deflection(vertices, near_features, "Strzalka_{0}".format(name))
        strzalki = strzalki.append(strzalka)
    "zlaczenie DataFrame z wczsniejszymi wynikami z DataFrame ze strzalkami"
    results = pd.concat([result.reset_index(drop=True), strzalki.T], axis=1)
    buildings = buildings.append(results)
    start = start + 1
    print("Wierzcholki dla budynku ", start, "gotowe!")
    #print(results)
"zapis do .csv"
buildings.to_csv("results.csv")








