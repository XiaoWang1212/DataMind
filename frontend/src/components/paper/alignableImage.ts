import { Image } from '@tiptap/extension-image'

export const AlignableImage = Image.extend({
  addAttributes () {
    return {
      ...this.parent?.(),
      align: {
        default: 'center',
        parseHTML: element => element.getAttribute('data-align') || 'center',
        renderHTML: attributes => ({
          'data-align': attributes.align,
        }),
      },
      width: {
        default: '100%',
        parseHTML: element => element.style.width || '100%',
        renderHTML: attributes => ({
          style: `width: ${attributes.width}`,
        }),
      },
    }
  },
})
