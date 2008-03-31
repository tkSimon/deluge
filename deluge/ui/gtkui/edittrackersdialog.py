#
# edittrackersdialog.py
#
# Copyright (C) 2007 Andrew Resch ('andar') <andrewresch@gmail.com>
# 
# Deluge is free software.
# 
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 2 of the License, or (at your option)
# any later version.
# 
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA    02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.

import gtk, gtk.glade
import pkg_resources

import deluge.common
from deluge.ui.client import aclient as client
import deluge.component as component
from deluge.log import LOG as log

class EditTrackersDialog:
    def __init__(self, torrent_id, parent=None):
        self.torrent_id = torrent_id
        self.glade = gtk.glade.XML(
                    pkg_resources.resource_filename("deluge.ui.gtkui", 
                                            "glade/edit_trackers.glade"))
        
        self.dialog = self.glade.get_widget("edit_trackers_dialog")
        self.treeview = self.glade.get_widget("tracker_treeview")
        self.add_tracker_dialog = self.glade.get_widget("add_tracker_dialog")
        self.add_tracker_dialog.set_transient_for(self.dialog)
        
        self.dialog.set_icon(deluge.common.get_logo(32))
        
        if parent != None:
            self.dialog.set_transient_for(parent)

        # Connect the signals
        self.glade.signal_autoconnect({
            "on_button_up_clicked": self.on_button_up_clicked,
            "on_button_add_clicked": self.on_button_add_clicked,
            "on_button_remove_clicked": self.on_button_remove_clicked,
            "on_button_down_clicked": self.on_button_down_clicked,
            "on_button_ok_clicked": self.on_button_ok_clicked,
            "on_button_cancel_clicked": self.on_button_cancel_clicked,
            "on_button_add_ok_clicked": self.on_button_add_ok_clicked,
            "on_button_add_cancel_clicked": self.on_button_add_cancel_clicked
        })
        
        # Create a liststore for tier, url
        self.liststore = gtk.ListStore(int, str)
        
        # Create the columns
        self.treeview.append_column(
            gtk.TreeViewColumn(_("Tier"), gtk.CellRendererText(), text=0))
        self.treeview.append_column(
            gtk.TreeViewColumn(_("Tracker"), gtk.CellRendererText(), text=1))

        self.treeview.set_model(self.liststore)            
        self.liststore.set_sort_column_id(0, gtk.SORT_ASCENDING)
        
    def run(self):
        # Make sure we have a torrent_id.. if not just return
        if self.torrent_id == None:
            return
            
        # Get the trackers for this torrent

        client.get_torrent_status(
            self._on_get_torrent_status, self.torrent_id, ["trackers"])
        client.force_call()

    def _on_get_torrent_status(self, status):
        """Display trackers dialog"""
        for tracker in status["trackers"]:
            self.add_tracker(tracker["tier"], tracker["url"])
            
        self.dialog.show()

    def add_tracker(self, tier, url):
        """Adds a tracker to the list"""
        self.liststore.append([tier, url])
    
    def get_selected(self):
        """Returns the selected tracker"""
        return self.treeview.get_selection().get_selected()[1]
        
    def on_button_up_clicked(self, widget):
        log.debug("on_button_up_clicked")
        selected = self.get_selected()
        num_rows = self.liststore.iter_n_children(None)
        if selected != None and num_rows > 1:
            tier = self.liststore.get_value(selected, 0)
            new_tier = tier + 1
            # Now change the tier for this tracker
            self.liststore.set_value(selected, 0, new_tier)
            
    def on_button_add_clicked(self, widget):
        log.debug("on_button_add_clicked")
        # Show the add tracker dialog
        self.add_tracker_dialog.show()
        self.glade.get_widget("entry_tracker").grab_focus()
        
    def on_button_remove_clicked(self, widget):
        log.debug("on_button_remove_clicked")
        selected = self.get_selected()
        if selected != None:
            self.liststore.remove(selected)
        
    def on_button_down_clicked(self, widget):
        log.debug("on_button_down_clicked")
        selected = self.get_selected()
        num_rows = self.liststore.iter_n_children(None)
        if selected != None and num_rows > 1:
            tier = self.liststore.get_value(selected, 0)
            if not tier > 0:
                return
            new_tier = tier - 1
            # Now change the tier for this tracker
            self.liststore.set_value(selected, 0, new_tier)
            
    def on_button_ok_clicked(self, widget):
        log.debug("on_button_ok_clicked")
        self.trackers = []
        def each(model, path, iter, data):
            tracker = {}
            tracker["tier"] = model.get_value(iter, 0)
            tracker["url"] = model.get_value(iter, 1)
            self.trackers.append(tracker)
        self.liststore.foreach(each, None)
        # Set the torrens trackers
        client.set_torrent_trackers(self.torrent_id, self.trackers)
        self.dialog.destroy()
        
    def on_button_cancel_clicked(self, widget):
        log.debug("on_button_cancel_clicked")
        self.dialog.destroy()
        
    def on_button_add_ok_clicked(self, widget):
        log.debug("on_button_add_ok_clicked")
        from re import search as re_search
        tracker = self.glade.get_widget("entry_tracker").get_text()
        if not re_search("https?://", tracker):
            # Bad url.. lets prepend http://
            tracker = "http://" + tracker
        
        # Figure out what tier number to use.. it's going to be the highest+1
        # Also check for duplicates
        self.highest_tier = 0
        self.duplicate = False
        def tier_count(model, path, iter, data):
            tier = model.get_value(iter, 0)
            if tier > self.highest_tier:
                self.highest_tier = tier
            tracker = model.get_value(iter, 1)
            if data == tracker:
                # We already have this tracker in the list
                self.duplicate = True

        # Check if there are any entries
        if self.liststore.iter_n_children(None) > 0:
            self.liststore.foreach(tier_count, tracker)
        else:
            self.highest_tier = -1
            
        # If not a duplicate, then add it to the list
        if not self.duplicate:
            # Add the tracker to the list
            self.add_tracker(self.highest_tier + 1, tracker)

        # Clear the entry widget and hide the dialog
        self.glade.get_widget("entry_tracker").set_text("")
        self.add_tracker_dialog.hide()
        
    def on_button_add_cancel_clicked(self, widget):
        log.debug("on_button_add_cancel_clicked")
        # Clear the entry widget and hide the dialog
        self.glade.get_widget("entry_tracker").set_text("")
        self.add_tracker_dialog.hide()        
