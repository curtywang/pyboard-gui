from typing import List, Dict, Tuple
import logging
import tkinter as tk
import pyboard as pyb
import serial
import serial.tools.list_ports


class PyboardGUI(tk.Frame):
    def __init__(self, master: tk.Tk = None):
        super().__init__(master)
        self.master = master
        self.master.minsize(800, 600)
        self.winfo_toplevel().title('Pyboard.py GUI')
        self.widgets = {}
        self.pyboard = None
        self.tk_vars = {}
        self.grid()
        self.create_widgets()

    def create_widgets(self):
        self.widgets['btn_hi'] = tk.Label(
            self,
            text="Pyboard.py GUI")
        self.widgets['btn_hi'].grid(
            row=0,
            column=0,
            sticky=tk.E)
        self.widgets['btn_quit'] = tk.Button(
            self,
            text="QUIT",
            command=self.quit_clean)
        self.widgets['btn_quit'].grid(
            row=0,
            column=1,
            sticky=tk.W)

        # Port widget group
        self.widgets['label_port'] = tk.Label(
            self,
            text='Serial port:')
        self.widgets['label_port'].grid(
            row=2,
            column=0,
            sticky=tk.E)
        ports = self.get_serial_ports()
        self.tk_vars['port'] = tk.StringVar(self)
        self.tk_vars['port'].set(ports[0])
        self.widgets['dropdown_port'] = tk.OptionMenu(
            self,
            self.tk_vars['port'],
            ports[0],
            *ports[1:])
        self.widgets['dropdown_port'].grid(
            row=2,
            column=1,
            sticky=tk.W)

        # Baudrate widget group
        self.widgets['label_baudrate'] = tk.Label(
            self, text='Baudrate:')
        self.widgets['label_baudrate'].grid(
            row=3,
            column=0,
            sticky=tk.E)
        baudrates = ["115200", "9600"]
        self.tk_vars['baudrate'] = tk.StringVar(self)
        self.tk_vars['baudrate'].set(baudrates[0])
        self.widgets['dropdown_baudrate'] = tk.OptionMenu(
            self,
            self.tk_vars['baudrate'],
            baudrates[0],
            *baudrates[1:])
        self.widgets['dropdown_baudrate'].grid(
            row=3,
            column=1,
            sticky=tk.W)

        # Connect widget group
        self.widgets['label_connect'] = tk.Label(
            self,
            text='Connect status: \nUnconnected',
            fg='red')
        self.widgets['label_connect'].grid(
            row=4,
            column=0,
            sticky=tk.E)
        self.widgets['btn_connect'] = tk.Button(
            self,
            text='Connect to Board',
            command=self.connect_to_board)
        self.widgets['btn_connect'].grid(
            row=4,
            column=1,
            sticky=tk.W)

        # Files listbox widget group
        self.widgets['label_files_board'] = tk.Label(
            self, text='Files on board:')
        self.widgets['label_files_board'].grid(
            row=0,
            column=2,
            sticky=tk.W)
        self.widgets['listbox_files_board'] = tk.Listbox(
            self, selectmode=tk.SINGLE)
        self.widgets['listbox_files_board'].grid(
            row=1,
            column=2,
            rowspan=10,
            sticky=tk.W)
        self.widgets['btn_refresh_files_board'] = tk.Button(
            self,
            text='Refresh files',
            command=self.update_files_board_listbox)
        self.widgets['btn_refresh_files_board'].grid(
            row=12, column=2, sticky=tk.W)
        self.widgets['btn_view_file_board'] = tk.Button(
            self,
            text='View selected file',
            command=self.view_file_board_listbox)
        self.widgets['btn_view_file_board'].grid(
            row=13, column=2, sticky=tk.W)

        # File view widget
        self.widgets['text_view_file_board'] = tk.Text(
            self, state=tk.DISABLED)
        self.widgets['text_view_file_board'].grid(
            row=0, column=3, rowspan=20, sticky=tk.W)

    def view_file_board_listbox(self):
        src_index = self.widgets['listbox_files_board'].curselection()
        src = self.widgets['listbox_files_board'].get(src_index).split(':')[0]
        filetext = self.pyboard_view_file(src)
        self.widgets['text_view_file_board']['state'] = tk.NORMAL
        self.widgets['text_view_file_board'].delete(1.0, tk.END)
        self.widgets['text_view_file_board'].insert(tk.END, filetext)
        self.widgets['text_view_file_board']['state'] = tk.DISABLED
        return

    def pyboard_view_file(self, src='', chunk_size=256) -> str:
        try:
            self.pyboard.enter_raw_repl()
            cmd = (
                    "with open('%s') as f:\n while 1:\n"
                    "  b=f.read(%u)\n  if not b:break\n  print(b,end='')" % (src, chunk_size)
            )
            filetext = self.pyboard.exec(cmd)
            self.pyboard.exit_raw_repl()
            return filetext.decode('utf8')
        except Exception as e:
            logging.exception(e)
            return ''

    def update_connect_text_and_buttons(self):
        if self.pyboard is not None:
            self.widgets['label_connect']['text'] = 'Connect status: \nConnected!'
            self.widgets['label_connect']['fg'] = 'green'
            self.widgets['btn_connect']['text'] = 'Disconnect'
            self.widgets['btn_connect']['command'] = self.destroy_pyboard
        else:
            self.widgets['label_connect']['text'] = 'Connect status: \nUnconnected'
            self.widgets['label_connect']['fg'] = 'red'
            self.widgets['btn_connect']['text'] = 'Connect to Board'
            self.widgets['btn_connect']['command'] = self.connect_to_board
        return

    def connect_to_board(self):
        conn_success = self.create_pyboard()
        if not conn_success:
            logging.error('Unable to connect!')
        else:
            self.update_connect_text_and_buttons()
            self.update_files_board_listbox()
        return

    def destroy_pyboard(self):
        if self.pyboard is None:
            return
        try:
            self.pyboard.close()
        except Exception as e:
            logging.exception(e)
        self.pyboard = None
        self.update_connect_text_and_buttons()
        return

    def create_pyboard(self):
        try:
            self.pyboard = pyb.Pyboard(self.tk_vars['port'].get(),
                                       self.tk_vars['baudrate'].get())
            return True
        except Exception as e:
            logging.exception(e)
            return False

    def update_files_board_listbox(self):
        self.widgets['listbox_files_board'].delete(0, tk.END)
        [self.widgets['listbox_files_board'].insert(tk.END, f'{filename}: {size}')
         for filename, size in self.pyboard_list_files().items()]
        return

    def pyboard_list_files(self, src='') -> Dict[str, int]:
        try:
            self.pyboard.enter_raw_repl()
            cmd = (
                    "import uos\nfor f in uos.ilistdir(%s):\n"
                    " print('{:12} {}{}'.format(f[3]if len(f)>3 else 0,f[0],'/'if f[1]&0x4000 else ''))"
                    % (("'%s'" % src) if src else "")
            )
            files = self.pyboard.exec(cmd)
            files = files.decode('utf8').split('\r\n')[0:-1]
            files = [x.strip() for x in files]
            files = {x.split(' ')[1]: int(x.split(' ')[0]) for x in files}
            self.pyboard.exit_raw_repl()
            return files
        except Exception as e:
            logging.exception(e)
            return {}

    def quit_clean(self):
        self.destroy_pyboard()
        self.master.destroy()

    def destroy(self):
        self.quit_clean()

    @staticmethod
    def get_serial_ports() -> List[str]:
        return [p.device for p in serial.tools.list_ports.comports()]


def run_main_window():
    root = tk.Tk()
    app = PyboardGUI(master=root)
    app.mainloop()
    return


if __name__ == '__main__':
    run_main_window()
