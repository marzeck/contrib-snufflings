import subprocess
import os
import tempfile
import shutil
from pyrocko.snuffling import Snuffling, Param, Switch
from pyrocko import util, gui_util, guts
from xmlMarker import *
from PyQt4.QtCore import QUrl 
from PyQt4.QtGui import QDesktopServices

g_counter = 0

def get_magnitude(event):
    if event.magnitude:
        mag = event.magnitude
    elif event.moment_tensor:
        mag = event.moment_tensor.magnitude
    else:
        mag = 0.
    return mag

def convert_event_marker(marker):
    ev = marker.get_event()
    depth = ev.depth
    if depth is None:
        depth = 0.0

    xmleventmarker = XMLEventMarker(eventname=ev.name,
                            longitude=ev.lon,
                            latitude=ev.lat,
                            origintime=util.time_to_str(ev.time),
                            depth=depth,
                            magnitude=get_magnitude(ev),
                            active=['no', 'yes'][marker._active])

    return xmleventmarker

class MapMaker(Snuffling):
    '''
    <html>
    <body>
    <h1>Create a map containing event and station locations using googlemaps.</h1>

    <p>
    Invokes the standard browser if "Open in external browser" is selected.
    Some browsers do not allow javascript to open and read the xml-file 
    containing the necessary information due to the "Same-Origin-Policy".
    In that case you need to reset your standard browser. I.e.: Firefox on
    Linux do: <tt>xdg-settings set default-web-browser firefox.desktop</tt>
    </p>
    <p>
    The plate boundary database is based on the work done by Peter Bird, who kindly permitted usage. <br>
    See: <i>50. Bird, P. (2003) An updated digital model of plate boundaries, Geochemistry Geophysics Geosystems, 4(3), 1027, doi:10.1029/2001GC000252.</i>
    <br>
    Also available at 
    <a href="http://peterbird.name/publications/2003_PB2002/2003_PB2002.htm">http://www.peterbird.name</a>
    <br>
    Please note, that in the current implementation the orogens (cross-hatched
    areas in 
    <a href="http://peterbird.name/publications/2003_PB2002/Figure_01.gif">figure 1</a>)
    are not distinguished from plate boundaries.  The orogens are meant to 
    mark areas where the plate model is known to be incomplete (and/or inapplicable).<br>
    This matter will be pointed out in future releases of this snuffling. 
    </p>
    </body>
    </html>
    '''
    def setup(self):
        self.set_name('Create Map in GoogleMaps')
        self.add_parameter(Switch('Only active event', 'only_active', False))
        self.add_parameter(Switch('Open in external browser',
                                  'open_external', False))

        self.set_live_update(False)

    def call(self):
        self.cleanup()

        viewer = self.get_viewer()

        if self.only_active:
            active_event, active_stations = \
            self.get_active_event_and_stations()
        else:
            active_event = None
            active_stations = viewer.stations.values()


        station_list=[]
        for stat in active_stations:
            if not util.match_nslc(viewer.blacklist, stat.nsl()):
                xml_station_marker = XMLStationMarker(
                    nsl='.'.join(stat.nsl()),
                    longitude = stat.lon,
                    latitude = stat.lat,
                    active = 'yes')

            station_list.append(xml_station_marker)

        active_station_list = StationMarkerList(stations=station_list)

        if self.only_active:
            markers = [viewer.get_active_event_marker()]
        else:
            markers = [m for m in viewer.get_markers()
                       if isinstance(m, gui_util.EventMarker)]

        ev_marker_list = []
        for m in markers:
            xmleventmarker = convert_event_marker(m)
            ev_marker_list.append(xmleventmarker)

        event_list=EventMarkerList(events= ev_marker_list)
        event_station_list = MarkerLists(
            station_marker_list=active_station_list,
            event_marker_list=event_list)

        event_station_list.validate()

        tempdir = tempfile.mkdtemp(dir=self.tempdir())

        for entry in ['loadxmldoc.js', 'map.html']:
            shutil.copy(os.path.join(self.module_dir(), entry),
                        os.path.join(tempdir, entry))

        markers_fn = os.path.join(tempdir, 'markers.xml')
        dump_xml(event_station_list, filename=markers_fn)

        url = 'file://' + tempdir + '/map.html'
        if self.open_external:
            QDesktopServices.openUrl(QUrl(url))
        else:
            global g_counter
            g_counter += 1
            self.web_frame(url, name='GoogleMaps %i' % g_counter)


def __snufflings__():
    return [ MapMaker() ]
