import headerStyles from '../components/layout/Header.module.css';

const validHeaderClass: string = headerStyles.header;

// @ts-expect-error -- typo should be rejected when CSS module typings are generated.
const invalidHeaderClass = headerStyles.heder;

void validHeaderClass;
void invalidHeaderClass;
