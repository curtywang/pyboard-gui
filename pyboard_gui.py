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
        self.widgets['btn_hi'] = tk.Label(self,
                                          text="Pyboard.py GUI")
        self.widgets['btn_hi'].grid(row=0,
                                    column=0,
                                    sticky=tk.E)
        self.widgets['btn_quit'] = tk.Button(self,
                                             text="QUIT",
                                             command=self.quit_clean)
        self.widgets['btn_quit'].grid(row=0,
                                      column=1,
                                      sticky=tk.W)

        # Port widget group
        self.widgets['label_port'] = tk.Label(self,
                                              text='Serial port:')
        self.widgets['label_port'].grid(row=2,
                                        column=0,
                                        sticky=tk.E)
        ports = self.get_serial_ports()
        self.tk_vars['port'] = tk.StringVar(self)
        self.tk_vars['port'].set(ports[0])
        self.widgets['dropdown_port'] = tk.OptionMenu(self,
                                                      self.tk_vars['port'],
                                                      ports[0],
                                                      *ports[1:])
        self.widgets['dropdown_port'].grid(row=2,
                                           column=1,
                                           sticky=tk.W)

        # Baudrate widget group
        self.widgets['label_baudrate'] = tk.Label(self,
                                                  text='Baudrate:')
        self.widgets['label_baudrate'].grid(row=3,
                                            column=0,
                                            sticky=tk.E)
        baudrates = ["115200", "9600"]
        self.tk_vars['baudrate'] = tk.StringVar(self)
        self.tk_vars['baudrate'].set(baudrates[0])
        self.widgets['dropdown_baudrate'] = tk.OptionMenu(self,
                                                          self.tk_vars['baudrate'],
                                                          baudrates[0],
                                                          *baudrates[1:])
        self.widgets['dropdown_baudrate'].grid(row=3,
                                               column=1,
                                               sticky=tk.W)

        # Connect widget group
        self.widgets['label_connect'] = tk.Label(self,
                                                 text='Connect status: \nUnconnected',
                                                 fg='red')
        self.widgets['label_connect'].grid(row=4,
                                           column=0,
                                           sticky=tk.E)
        self.widgets['btn_connect'] = tk.Button(self,
                                                text='Connect to Board',
                                                command=self.connect_to_board)
        self.widgets['btn_connect'].grid(row=4,
                                         column=1,
                                         sticky=tk.W)

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

    def quit_clean(self):
        self.destroy_pyboard()
        self.master.destroy()

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
