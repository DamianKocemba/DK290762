import arcpy
import numpy as np
import pandas as pd


arcpy.env.overwriteOutput=1
arcpy.env.workspace = r"C:\Python_proj\dane"
path = "C:/PPGII/EGZAMIN/wyniki/"
file = r"C:\Python_proj\dane\BUBD.shp"



" ---------- WYBOR BUDYNKU ---------- "
"wybor kolumny z identyfikatorem budynku - domyslnie: gmlId"
col_id = "gmlID"
"wybor Id budynku"
building_id = ["PL.PZGIK.BDOT10k.BUBDA.18.6317726"]



"funkcja wybierajaca dany budynek z pliku BUBD.shp"
def select(table, value):
    arcpy.MakeFeatureLayer_management(table, "lyr")
    selection = arcpy.SelectLayerByAttribute_management("lyr", "NEW_SELECTION", "gmlId = '{0}'".format(value))
    return selection

cursor = arcpy.SearchCursor(file)
"itracja przez tabele"
buildings = {}
for row in cursor:
    "pobranie wartosci z kolumny z identyfiaktorem"
    value = row.getValue(col_id)
    if value in building_id:
        selection = select(file, value)
        #print(value)
        bldg_id = value.split('.')[-1]
        "zapisanie wierzcholkow budynku do pliku (plik z punktami) o nazwie 'result_ostatni_elem_identyf_gmlId.shp' "
        buildings['bldg_{0}'.format(bldg_id)] = arcpy.FeatureVerticesToPoints_management(selection, path+"result_{0}.shp".format(bldg_id))

def minimal_geometry(in_featre, name):
    min_geom = []
    rectangle_by_area = arcpy.MinimumBoundingGeometry_management(in_featre, path+name+'_RcByAr.shp', "RECTANGLE_BY_AREA")
    min_geom.append(rectangle_by_area)




"utworzenie DataFrame do zapisu danych o punktach"
results = pd.DataFrame()
for key, value in buildings.items():
    print(key)
    cursor = arcpy.da.SearchCursor(value, ['FID', 'gmlId', 'SHAPE@XY'])
    "iteracja przez kolejne punkty"
    for row in cursor:
        point_id = row[0]
        if point_id == arcpy.GetCount_management(value):
            next_point = row[0]
        else:
            next_point = point_id + 1
        identyfikator_bud = row[1]
        coordX = row[2][0]
        coordY = row[2][1]
        print("ID: ", point_id, 'Identyfikator:', identyfikator_bud, "Kolejny_wierzcolek: ", next_point,
              "X: ",coordX,"Y: ", coordY)
        "dopisanie kolejnych wierszy do DataFrame"
        results = results.append(pd.Series(data=[int(point_id), identyfikator_bud, int(next_point), coordX, coordY], name=row[0],
                                           index=['Id_pkt', 'Identyfikator_budynku', 'Nr_kolejnego_wierzcholka', 'X', 'Y']))

    arcpy.MinimumBoundingGeometry_management(value, path+key+'_RcByAr.shp', "CIRCLE", "ALL")
    arcpy.MinimumBoundingGeometry_management(value, path + key + '_ConHul.shp', "CONVEX_HULL", "ALL")

print(results)

def segment_length(col_x, col_y, value1, value2):
    "col_x, col_y - kolumny z wartosciami X i Y, value1=1 dla dlugosci segmentu 'przed', value1=-1 dla segmentu 'po'"
    length = np.sqrt((col_x.shift(value1) - col_x.shift(value2))**2 + (col_y.shift(value1) - col_y.shift(value2))**2)
    return length


def vertex_angle(col_x, col_y):
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

"obliczenie dla kazdego punktu dlugosci segmentu 'przed' "
results['length_in'] = segment_length(results['X'], results['Y'], 1, 0)
"pierwszy punkt z ostatnim sie pokrywaja (sa takie same), dlatego przypisano mu wartosc dla punktu pierwszego"
results['length_in'] = results.length_in.fillna(results['length_in'].iloc[-1])


"obliczenie dla kazdego punktu dlugosci segmentu 'po' "
results['length_out'] = segment_length(results['X'], results['Y'], -1, 0)
"pierwszy punkt z ostatnim sie pokrywaja (sa takie same), dlatego przypisano mu wartosc dla punktu pierwszego"
results['length_out'] = results.length_out.fillna(results['length_out'].iloc[0])

results['angle_in'] = vertex_angle(results['X'], results['Y'])

print(results)









