import arcpy
import numpy as np
import pandas as pd

def segment_length(col_x, col_y, value1, value2):
    "col_x, col_y - kolumny z wartosciami X i Y, value1=1 dla dlugosci segmentu 'przed', value1=-1 dla segmentu 'po'"
    "col_x i col_y to kolumny DataFrame"
    length = np.sqrt((col_x.shift(value1) - col_x.shift(value2))**2 + (col_y.shift(value1) - col_y.shift(value2))**2)
    return length

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

def minimal_geometry(in_featre, name):
    "dane wejsciowe: in_feature - budynek w .shp, name: nazwa budynku (identyfikator)"
    min_geom = {}
    "minimalna otoczka - RECTANGLE BY AREA"
    rectangle_by_area = result_path+name+'_RecByArea.shp'
    arcpy.MinimumBoundingGeometry_management(in_featre, rectangle_by_area, "RECTANGLE_BY_AREA", "ALL")
    min_geom["RectangleByArea"] = rectangle_by_area

    "minimalna otoczka - RECTANGLE BY WIDTH"
    rectangle_by_width = result_path+name+'_RecByWidth.shp'
    arcpy.MinimumBoundingGeometry_management(in_featre, rectangle_by_width, "RECTANGLE_BY_WIDTH", "ALL")
    min_geom["RectangleByWidth"] = rectangle_by_width

    "minimalna otoczka - CONVEX HULL"
    convex_hull = result_path+name+'_ConvHull.shp'
    arcpy.MinimumBoundingGeometry_management(in_featre, convex_hull, "CONVEX_HULL", "ALL")
    min_geom["ConvexHull"] = convex_hull

    "minimalna otoczka - CRCLE"
    circle = result_path+name+'_Circle.shp'
    arcpy.MinimumBoundingGeometry_management(in_featre, circle, "CIRCLE", "ALL")
    min_geom["Circle"] = circle

    "minimalna otoczka - ENVELOPE"
    envelope = result_path+name+'_Envelope.shp'
    arcpy.MinimumBoundingGeometry_management(in_featre, envelope, "ENVELOPE", "ALL")
    min_geom["Envelope"] = envelope
    return min_geom

def deflection(vertices_class, polygon_class):
    "zamiana  MBG na linie"
    arcpy.PolygonToLine_management(polygon_class, "line.shp")
    "odleglosc do linii"
    arcpy.Near_analysis(vertices_class, "line.shp")
    "wybranie kolumny z odlegloscia i zapisanie jej do obiektu Series"
    cursor = arcpy.da.SearchCursor(vertices_class, ["NEAR_DIST"])
    list = [row[0] for row in cursor]
    del row, cursor
    distance = pd.Series(list)
    arcpy.Delete_management("line.shp")
    return distance

"funkcja wybierajaca dany budynek z pliku BUBD.shp"
def select(table, value):
    "table - oryginalny BUBD.shp, value - identyfikator gmlId"
    arcpy.MakeFeatureLayer_management(table, "lyr")
    selection = arcpy.SelectLayerByAttribute_management("lyr", "NEW_SELECTION", "gmlId = '{0}'".format(value))
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

arcpy.env.overwriteOutput=1
arcpy.env.workspace = r"C:/Python_proj/dane2/"
path = "C:/Python_proj/dane2/"
result_path = path+"wyniki/"
file = "BUBD.shp"

" ---------- WYBOR BUDYNKU ---------- "
"lista z gmlId budynku"
building_id = ["PL.PZGIK.BDOT10k.BUBDA.18.6325983", "PL.PZGIK.BDOT10k.BUBDA.18.6319873"]
#building_id = [str(line.getValue("gmlId")) for line in arcpy.SearchCursor(file)]

cursor = arcpy.SearchCursor(file)
#buildings = {}
"DataFrame na wszystkie wyniki"
results_all = pd.DataFrame()
start = 0
for row in cursor:
    buildings = {}
    "pobranie wartosci z kolumny z identyfiaktorem"
    value = str(row.getValue("gmlId"))
    if value in building_id:
        selection = select(file, value)
        #print(value)
        bldg_id = value.split('.')[-1]
        "zapisanie wierzcholkow budynku do pliku (plik z punktami) o nazwie 'result_ostatni_elem_identyf_gmlId.shp' "
        buildings['bldg_{0}'.format(bldg_id)] = arcpy.FeatureVerticesToPoints_management(selection, result_path+"result_{0}.shp".format(bldg_id))

        for id_bud, vertices_bud in buildings.items():
            "utworzenie DataFrame do zapisu danych o punktach"
            results = pd.DataFrame()
            start += 1
            print(start, "- ok")
            cursor = arcpy.da.SearchCursor(vertices_bud, ['FID', 'gmlId', 'SHAPE@XY'])
            "iteracja przez kolejne punkty"
            for row in cursor:
                point_id = row[0]
                if point_id == arcpy.GetCount_management(vertices_bud):
                    next_point = row[0]
                else:
                    next_point = point_id + 1
                identyfikator_bud = row[1]
                coordX = row[2][0]
                coordY = row[2][1]

                "dopisanie kolejnych wierszy do DataFrame"
                results = results.append(
                    pd.Series(data=[int(point_id), identyfikator_bud, int(next_point), coordX, coordY], name=row[0],
                              index=['Id_pkt', 'Identyfikator_budynku', 'Nr_kolejnego_wierzcholka', 'X', 'Y']))

            "dolaczenie atrybutow length_in, length_out"
            length_in_out_angle(results)
            "ponizsza funkcja tworzy liste minimalnych geometrii dla budynku"
            MBG_dict = minimal_geometry(vertices_bud, id_bud)
            "iteracja przez slownik - nazwa: klasa_MBG"
            for name, mbg in MBG_dict.items():
                results["Strzalka_{0}".format(name)] = deflection(vertices_bud, mbg)
                "usuniecie niepotrzebnych juz warstw"
                arcpy.Delete_management(mbg)
            arcpy.Delete_management(vertices_bud)

            results_all = results_all.append(results)


results_all.to_csv("results.csv")









