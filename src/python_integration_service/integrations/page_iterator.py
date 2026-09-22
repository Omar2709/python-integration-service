class PageIterator:
    def __init__(self, pages: list[list[dict]]) -> None:
        self.pages = pages
        self.page_index = 0
        self.item_index = 0

    def __iter__(self) -> "PageIterator":
        return self

    def __next__(self) -> dict:
        while self.page_index < len(self.pages):
            current_page = self.pages[self.page_index]

            if self.item_index < len(current_page):
                item = current_page[self.item_index]
                self.item_index += 1
                return item

            self.page_index += 1
            self.item_index = 0

        raise StopIteration
