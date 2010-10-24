"""GUI for Aspen.
"""
import os
import subprocess


import wx
from aspen import configure
from aspen.server import Server



#from ICO import ICO
#ICO = base64.b64decode(ICO)


HELP = "Locate your Aspen website root, and click 'Start Aspen'."
TITLE = "gAspen"


# wxPython classes
# ================

class AspenPanel(wx.Panel):
    def __init__(self, frame):
        wx.Panel.__init__(self, frame)

        sizer = wx.FlexGridSizer(4,1,5,5)
#        self.box1 = wx.StaticBox(self, label="Step 1")
#        self.box2 = wx.StaticBox(self, label="Step 2")

        tree = wx.GenericDirCtrl(self, size=wx.Size(300,100))
        button = wx.Button(self, label="Start Aspen")
        button.Bind(wx.EVT_BUTTON, self.on_start)

        sizer.Add( wx.StaticText(self, label=HELP)
                 , flag=wx.EXPAND
                  )
        sizer.Add( tree 
                 , flag=wx.EXPAND|wx.ALIGN_CENTER
                  )
        sizer.Add(button, flag=wx.ALIGN_CENTER)
        self.SetSizerAndFit(sizer)

        self.tree = tree
        self.frame = frame


    def on_start(self, evt):
        """Process the file, with minimal error handling.
        """
        try:
            self._on_start()
        except:
            import traceback
            traceback.print_exc()


    def _on_start(self):
        """        
        """

        root = self.tree.GetPath()
        root = os.path.realpath(root)
        configuration = configure([ '--root=%s' % root
                                  , '--log-level=DEBUG' 
                                   ])
        server = Server(configuration)
        server.start()


        # All done
        # ========

        self.frame.Close()


class AspenFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title=TITLE)
        panel = AspenPanel(self)


        # Set icon
        # ========
        # Store in module and use temp dir for distributability.

#        dir = tempfile.gettempdir()
#        ico = os.path.join(dir, 'ADPGremlin.ico')
#        fp = open(ico, 'wb+')
#        fp.write(ICO)
#        fp.close()
#
#        ib = wx.IconBundle()
#        ib.AddIconFromFile(ico, wx.BITMAP_TYPE_ICO)
#        self.SetIcons(ib)
#
#        os.remove(ico)


def main():
    app = wx.App()
    try:
        frame = AspenFrame()
        frame.Show()
    except:
        import traceback
        traceback.print_exc()
    app.MainLoop()
    
