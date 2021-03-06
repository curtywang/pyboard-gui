from typing import List, Dict, Set, Any
import logging
import tkinter as tk
from tkinter.ttk import Progressbar
import tkinter.filedialog as tkfd
import tkinter.messagebox as tkmb
import tkinter.scrolledtext as tkst
import pyboard as pyb
import serial
import serial.tools.list_ports
import os
import sys
from io import StringIO
import copy


class StdoutRedirector(StringIO):
    def __init__(self, text_widget: tk.Text):
        super().__init__()
        self.text_space = text_widget

    def write(self, string: Any):
        self.text_space.configure(state=tk.NORMAL)
        self.text_space.insert(tk.END, string)
        self.text_space.see(tk.END)
        self.text_space.configure(state=tk.DISABLED)
        if type(string) != str and '\n' in string.decode('utf8'):
            self.text_space.update_idletasks()


class PyboardGUI(tk.Frame):
    def __init__(self, master: tk.Tk = None):
        super().__init__(master)
        self.master = master
        self.master.minsize(800, 600)
        self.master.rowconfigure(0, weight=3)
        self.master.columnconfigure(0, weight=3)
        self.winfo_toplevel().title('Pyboard.py GUI')
        self.master.protocol("WM_DELETE_WINDOW", self.quit_clean)
        self.widgets = {}
        self.frames = {}
        self.board_widgets = {}
        self.console_widgets = {}
        self.pyboard = None
        self.tk_vars = {}
        self.grid(sticky=tk.NSEW, column=0, row=0)
        self.columnconfigure(2, weight=3)
        self.rowconfigure(1, weight=3)
        self.create_widgets()
        self.create_board_widgets()
        self.create_view_widgets()
        self.create_console_widgets()
        self.create_program_log_widgets()
        self.disable_board_widgets()
        self.disable_console_widgets()
        self.update_serial_ports()
        self.lift()
        self.safe_files = ['boot.py']
        self.logging_redirector = StdoutRedirector(self.console_widgets['log'])
        logging.basicConfig(format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=logging.INFO,
                            stream=self.logging_redirector)
        sys.stdout = self.logging_redirector
        sys.stderr = self.logging_redirector
        self.serial_redirector = StdoutRedirector(self.console_widgets['text_serial'])
        pyb.reset_stdout(self.serial_redirector)
        logging.info('Pyboard.py GUI initialized!')

    def create_widgets(self):
        self.frames['connect'] = tk.LabelFrame(
            self,
            text='Board connection',
            padx=5,
            pady=5
        )
        self.frames['connect'].grid(
            row=0, column=0, sticky=tk.NW)
        self.widgets['btn_hi'] = tk.Label(
            self.frames['connect'],
            text="Pyboard.py GUI")
        self.widgets['btn_hi'].grid(
            row=0,
            column=0,
            sticky=tk.E)
        self.widgets['btn_quit'] = tk.Button(
            self.frames['connect'],
            text="QUIT",
            command=self.quit_clean)
        self.widgets['btn_quit'].grid(
            row=0,
            column=1,
            sticky=tk.W)

        # Port widget group
        self.widgets['label_port'] = tk.Label(
            self.frames['connect'],
            text='Serial port:')
        self.widgets['label_port'].grid(
            row=2,
            column=0,
            sticky=tk.E)
        self.tk_vars['port'] = tk.StringVar(self)
        self.widgets['dropdown_port'] = tk.OptionMenu(
            self.frames['connect'],
            self.tk_vars['port'],
            '')
        self.widgets['dropdown_port'].grid(
            row=2,
            column=1,
            sticky=tk.W)

        # Baudrate widget group
        self.widgets['label_baudrate'] = tk.Label(
            self.frames['connect'], text='Baudrate:')
        self.widgets['label_baudrate'].grid(
            row=3,
            column=0,
            sticky=tk.E)
        baudrates = ["115200", "9600"]
        self.tk_vars['baudrate'] = tk.StringVar(self)
        self.tk_vars['baudrate'].set(baudrates[0])
        self.widgets['dropdown_baudrate'] = tk.OptionMenu(
            self.frames['connect'],
            self.tk_vars['baudrate'],
            baudrates[0],
            *baudrates[1:])
        self.widgets['dropdown_baudrate'].grid(
            row=3,
            column=1,
            sticky=tk.W)

        # Connect widget group
        self.widgets['label_connect'] = tk.Label(
            self.frames['connect'],
            text='Connect status: \nUnconnected',
            fg='red')
        self.widgets['label_connect'].grid(
            row=4,
            column=0,
            sticky=tk.E)
        self.widgets['btn_connect'] = tk.Button(
            self.frames['connect'],
            text='Connect to Board',
            command=self.connect_to_board)
        self.widgets['btn_connect'].grid(
            row=4,
            column=1,
            sticky=tk.W)

    @staticmethod
    def get_optionmenu_options(optionmenu: tk.OptionMenu) -> Set[str]:
        return {optionmenu['menu'].entrycget(idx, 'label')
                for idx in range(optionmenu['menu'].index(tk.END) + 1)}

    def update_serial_ports(self):
        ports = self.get_serial_ports()
        current_options = self.get_optionmenu_options(self.widgets['dropdown_port'])
        if current_options != ports:
            self.widgets['dropdown_port']['menu'].delete(0, tk.END)
            if len(ports) > 0:
                for p in ports:
                    self.widgets['dropdown_port']['menu'].add_command(
                        label=p, command=lambda new_value=p: self.tk_vars['port'].set(new_value))
                self.tk_vars['port'].set(self.widgets['dropdown_port']['menu'].entrycget(0, 'label'))
            if self.pyboard is not None:
                self.destroy_pyboard()
        self.master.after(500, self.update_serial_ports)

    def create_board_widgets(self):
        self.frames['management'] = tk.LabelFrame(
            self,
            text='Board management',
            padx=5,
            pady=5
        )
        self.frames['management'].grid(
            row=0, column=1, sticky=tk.NW)

        # Files listbox widget group
        self.frames['files_board'] = tk.LabelFrame(
            self.frames['management'], text='Files on board:')
        self.frames['files_board'].grid(
            row=0,
            column=0,
            sticky=tk.W)
        self.board_widgets['listbox_files'] = tk.Listbox(
            self.frames['files_board'], selectmode=tk.SINGLE,
            height=5)
        self.board_widgets['listbox_files'].grid(
            row=0,
            column=0,
            sticky=tk.W)
        self.board_widgets['btn_refresh_files'] = tk.Button(
            self.frames['management'],
            text='Refresh files',
            command=self.update_files_board_listbox)
        self.board_widgets['btn_refresh_files'].grid(
            row=1, column=0, sticky=tk.W)
        self.board_widgets['btn_view_file'] = tk.Button(
            self.frames['management'],
            text='View selected file',
            command=self.view_file_board_listbox)
        self.board_widgets['btn_view_file'].grid(
            row=2, column=0, sticky=tk.W)
        self.board_widgets['btn_upload_file'] = tk.Button(
            self.frames['management'],
            text='Upload file to board',
            command=self.upload_file_board)
        self.board_widgets['btn_upload_file'].grid(
            row=3, column=0, sticky=tk.W)
        self.board_widgets['btn_delete_file'] = tk.Button(
            self.frames['management'],
            text='Delete selected file',
            command=self.delete_file_board)
        self.board_widgets['btn_delete_file'].grid(
            row=4, column=0, sticky=tk.W, pady=4)

    def create_view_widgets(self):
        self.frames['file_view'] = tk.LabelFrame(
            self,
            text='File view',
            padx=5,
            pady=5
        )
        self.frames['file_view'].grid(
            row=0, column=2, sticky=tk.W+tk.E+tk.S+tk.N)
        self.frames['file_view'].columnconfigure(0, weight=3)

        # File view widget
        self.board_widgets['text_view_file'] = tkst.ScrolledText(
            self.frames['file_view'], state=tk.DISABLED, height=12, width=50, wrap="none")
        self.board_widgets['text_view_file'].grid(
            row=0, column=0, sticky=tk.NSEW)

    def create_console_widgets(self):
        self.frames['console'] = tk.LabelFrame(
            self,
            text='Serial console',
            padx=5,
            pady=5
        )
        self.frames['console'].grid(
            row=1, column=0, columnspan=3, sticky=tk.NSEW)
        self.frames['console'].columnconfigure(1, weight=3)
        self.frames['console'].rowconfigure(0, weight=3)

        # Console widget
        self.console_widgets['text_serial'] = tkst.ScrolledText(
            self.frames['console'], state=tk.DISABLED, height=15, width=100,
            bg='black', fg='white')
        self.console_widgets['text_serial'].grid(
            row=0, column=0, columnspan=3, sticky=tk.NSEW)

        # Console entry
        self.console_widgets['entry_serial'] = tkst.ScrolledText(
            self.frames['console'],
            width=80, height=2,
            font='TkFixedFont')
        self.console_widgets['entry_serial'].grid(
            row=1, column=0, columnspan=3, sticky=tk.NSEW, ipadx=1, ipady=1)
        self.console_widgets['entry_serial'].bind(
            '<Control-Return>', lambda x: self.send_console_command())

        self.console_widgets['btn_send_command'] = tk.Button(
            self.frames['console'],
            text='Send command',
            command=self.send_console_command)
        self.console_widgets['btn_send_command'].grid(
            row=2, column=2, sticky=tk.SE, padx=4)

        # Exec host file
        self.console_widgets['btn_exec_file'] = tk.Button(
            self.frames['console'],
            text='Pick and run file from host',
            command=self.exec_host_file_board)
        self.console_widgets['btn_exec_file'].grid(
            row=2, column=0, sticky=tk.SW, padx=4)

    def send_console_command(self):
        typed_command = copy.deepcopy(self.console_widgets['entry_serial'].get('1.0', tk.END))
        self.console_widgets['entry_serial'].delete(1.0, tk.END)
        self.serial_redirector.write(f'>> {typed_command}\n')
        self.console_widgets['text_serial'].update_idletasks()
        self.exec_command(typed_command)
        return 'break'  # needed to prevent extra newline inside text widget

    def create_program_log_widgets(self):
        self.frames['log'] = tk.LabelFrame(
            self,
            text='Program log',
            padx=5,
            pady=5
        )
        self.frames['log'].grid(
            row=2, column=0, columnspan=3, sticky=tk.NSEW)
        self.frames['log'].columnconfigure(0, weight=3)
        self.frames['log'].rowconfigure(0, weight=3)

        # Logging widget
        self.console_widgets['log'] = tkst.ScrolledText(
            self.frames['log'], state=tk.DISABLED, height=5, width=100)
        self.console_widgets['log'].grid(
            row=0, column=0, sticky=tk.NSEW)

    def disable_board_widgets(self):
        for widget in self.board_widgets.values():
            widget['state'] = tk.DISABLED

    def disable_console_widgets(self):
        for widget in self.console_widgets.values():
            widget['state'] = tk.DISABLED

    def enable_board_widgets(self):
        for widget in self.board_widgets.values():
            widget['state'] = tk.NORMAL

    def enable_console_widgets(self):
        for widget in self.console_widgets.values():
            widget['state'] = tk.NORMAL
        self.console_widgets['text_serial']['state'] = tk.DISABLED
        self.console_widgets['log']['state'] = tk.DISABLED

    # def exec_selected_file_board(self):
    #     try:
    #         filename = self.get_selected_file_board_listbox()
    #         self.pyboard.enter_raw_repl()
    #         self.pyboard.exec(src=filename)
    #         self.pyboard.exit_raw_repl()
    #         self.update_files_board_listbox()
    #     except Exception as e:
    #         logging.exception(e)
    #         tkmb.showerror(title='Error!',
    #                        message='Error deleting file!')
    #     return

    def exec_command(self, command: str):
        try:
            self.pyboard.enter_raw_repl()
            ret = self.pyboard.exec_(
                command, data_consumer=pyb.stdout_write_bytes)
            self.pyboard.exit_raw_repl()
            return ret
        except Exception as e:
            logging.exception(e)
            tkmb.showerror(title='Error!',
                           message='Error running command!')
        return

    def exec_host_file_board(self):
        try:
            selected_file = tkfd.askopenfile(defaultextension='py')
            filename = selected_file.name
            self.pyboard.enter_raw_repl()
            self.pyboard.exec(src=filename)
            self.pyboard.exit_raw_repl()
            self.update_files_board_listbox()
        except Exception as e:
            logging.exception(e)
            tkmb.showerror(title='Error!',
                           message='Error deleting file!')
        return

    def upload_file_board(self, safemode=True):
        selected_file = tkfd.askopenfile(defaultextension='py')
        filename = os.path.basename(selected_file.name)
        filepath = selected_file.name
        if safemode and filename in self.safe_files:
            tkmb.showerror(title='Error!',
                           message='Cannot delete protected file!')
            return
        try:
            self.pyboard.enter_raw_repl()
            self.pyboard.fs_put(src=filepath, dest=filename)
            self.pyboard.exit_raw_repl()
            self.update_files_board_listbox()
        except Exception as e:
            logging.exception(e)
            tkmb.showerror(title='Upload error!',
                           message='Error uploading file!')
        return

    def delete_file_board(self, safemode=True):
        try:
            filename = self.get_selected_file_board_listbox()
            if safemode and filename in self.safe_files:
                tkmb.showerror(title='Error!',
                               message='Cannot delete protected file!')
                return
            self.pyboard.enter_raw_repl()
            self.pyboard.fs_rm(src=filename)
            self.pyboard.exit_raw_repl()
            self.update_files_board_listbox()
        except Exception as e:
            logging.exception(e)
            tkmb.showerror(title='Error!',
                           message='Error deleting file!')
        return

    def get_selected_file_board_listbox(self):
        src_index = self.board_widgets['listbox_files'].curselection()
        src = self.board_widgets['listbox_files'].get(src_index).split(':')[0]
        return src

    def view_file_board_listbox(self):
        src = self.get_selected_file_board_listbox()
        filetext = self.pyboard_view_file(src)
        self.board_widgets['text_view_file']['state'] = tk.NORMAL
        self.board_widgets['text_view_file'].delete(1.0, tk.END)
        self.board_widgets['text_view_file'].insert(tk.END, filetext)
        self.board_widgets['text_view_file']['state'] = tk.DISABLED
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
            logging.info('MicroPython board connected!')
        else:
            self.widgets['label_connect']['text'] = 'Connect status: \nUnconnected'
            self.widgets['label_connect']['fg'] = 'red'
            self.widgets['btn_connect']['text'] = 'Connect to Board'
            self.widgets['btn_connect']['command'] = self.connect_to_board
            logging.info('MicroPython board disconnected!')
        return

    def connect_to_board(self):
        conn_success = self.create_pyboard()
        if not conn_success:
            logging.error('Unable to connect!')
        else:
            self.update_connect_text_and_buttons()
            self.enable_board_widgets()
            self.enable_console_widgets()
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
        self.disable_board_widgets()
        self.disable_console_widgets()
        self.update_serial_ports()
        return

    def create_pyboard(self):
        try:
            self.pyboard = pyb.Pyboard(self.tk_vars['port'].get(),
                                       self.tk_vars['baudrate'].get())
            return True
        except Exception as e:
            logging.exception(e)
            tkmb.showerror('Creation failed!', 'Double-check that the baudrate is correct.')
            return False

    def update_files_board_listbox(self):
        self.board_widgets['listbox_files'].delete(0, tk.END)
        [self.board_widgets['listbox_files'].insert(tk.END, f'{filename}: {size}')
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

    @staticmethod
    def get_serial_ports() -> Set[str]:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if len(ports) < 1:
            return {'', }
        else:
            return set(ports)


def run_main_window():
    root = tk.Tk()
    app = PyboardGUI(master=root)
    app.mainloop()
    return


if __name__ == '__main__':
    run_main_window()
