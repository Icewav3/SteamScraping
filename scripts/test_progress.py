from src.BaseScraper import BaseScraper
from src.FileSystem import FileSystem

class Dummy(BaseScraper):
    async def scrape(self):
        return 0

def main():
    fs = FileSystem(data_dir='Data/test')
    d = Dummy(fs)
    it = d.progress_bar(list(range(5)), 'testing')
    print('Iterator type:', type(it))
    for i in it:
        print('item', i)

if __name__ == '__main__':
    main()
