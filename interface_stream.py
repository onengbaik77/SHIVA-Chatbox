import tkinter as tk
import queue

from interface import ShivaInterface


class ShivaStreamingInterface(ShivaInterface):

    def process_message(self, user_input):
        try:
            self.response_queue.put(("start", None))

            for chunk in self.brain.process_stream(user_input):
                self.response_queue.put(("chunk", chunk))

            self.response_queue.put(("done", None))

        except Exception as error:
            self.response_queue.put(
                ("chunk", f"Terjadi error: {error}")
            )
            self.response_queue.put(("done", None))

    def check_response_queue(self):
        try:
            while True:
                event_type, data = self.response_queue.get_nowait()

                if event_type == "start":
                    self.chat.configure(state="normal")

                    self.chat.insert(
                        tk.END,
                        "SHIVA: ",
                        "name"
                    )

                    self.chat.configure(state="disabled")
                    self.chat.see(tk.END)

                elif event_type == "chunk":
                    self.chat.configure(state="normal")

                    self.chat.insert(
                        tk.END,
                        data,
                        "message"
                    )

                    self.chat.configure(state="disabled")
                    self.chat.see(tk.END)

                elif event_type == "done":
                    self.chat.configure(state="normal")

                    self.chat.insert(
                        tk.END,
                        "\n\n",
                        "message"
                    )

                    self.chat.configure(state="disabled")
                    self.chat.see(tk.END)

                    self.entry.configure(state="normal")

                    self.send_button.configure(
                        state="normal",
                        text="Send"
                    )

                    self.entry.focus_set()

        except queue.Empty:
            pass

        self.root.after(
            50,
            self.check_response_queue
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = ShivaStreamingInterface(root)
    root.mainloop()